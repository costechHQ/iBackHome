"""Shared test fixtures for every test under backend/ (tests/ and each feature's tests/). Owner: Christopher.

    async def test_something(db_session):            # real Postgres, rolled back after the test
        ...

    async def test_endpoint(client):                 # HTTP calls into the app, same rolled-back session
        response = await client.post("/api/v1/...", json={...})

Tests run against DATABASE_URL (locally: `docker compose up db`), migrated to head once per run.
If the database is unreachable, DB tests are skipped locally but FAIL in CI, so a missing database
can never make CI look green. A feature's own conftest.py can still override these fixtures.
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.db import CONNECT_TIMEOUT_SECONDS, get_session

# Async psycopg can't run on Windows' default Proactor loop; Linux (CI, Docker) is unaffected.
# Set globally so Alembic's asyncio.run() below gets the right loop too.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BACKEND_DIR = Path(__file__).parent


def _database_unavailable(reason: str) -> None:
    if os.environ.get("CI"):
        pytest.fail(f"database required in CI: {reason}")
    pytest.skip(f"database not reachable: {reason}")


@pytest.fixture(scope="session")
def migrated_database() -> Iterator[None]:
    """Bring the test database to the latest migration once per test run."""
    # Quick reachability probe first: Alembic's own connect has no timeout.
    probe = create_engine(
        get_settings().database_url, connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS}
    )
    try:
        with probe.connect():
            pass
    except Exception as exc:  # noqa: BLE001
        _database_unavailable(exc.__class__.__name__)
    finally:
        probe.dispose()

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    try:
        command.upgrade(config, "head")
    except Exception as exc:  # noqa: BLE001 - any failure here means "no usable database"
        _database_unavailable(f"{exc.__class__.__name__}: {exc}")
    yield


@pytest.fixture
async def db_session(migrated_database: None) -> AsyncIterator[AsyncSession]:
    """A session inside a transaction that is rolled back after the test.

    Code under test may call session.commit(): it only releases a savepoint, so nothing persists.
    """
    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )
    try:
        connection = await engine.connect()
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        _database_unavailable(exc.__class__.__name__)
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """HTTP client for the app; every request uses the test's rolled-back db_session."""
    from app.main import app

    async def _test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _test_session
    # raise_app_exceptions=False lets tests see the JSON 500 response instead of the raw exception.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture(autouse=True)
def _subscription_not_required(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Most tests approve a BoQ without a Stripe subscription; subscription tests switch it back on."""
    from app.features.subscriptions.settings import get_subscription_settings

    monkeypatch.setenv("SUBSCRIPTION_REQUIRED", "false")
    get_subscription_settings.cache_clear()
    yield
    get_subscription_settings.cache_clear()
