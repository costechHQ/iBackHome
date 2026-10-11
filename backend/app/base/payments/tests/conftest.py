"""Fixtures for payments tests, against the real Postgres + PostGIS database.

DATABASE_URL must point at a database migrated with `alembic upgrade head` (CI does this).
Tests are skipped when no database is reachable.

- `db_session`: one transaction, rolled back at the end. The deferred balance trigger never
  fires here because nothing commits; use it for service-level checks.
- `session_factory` / `engine`: real commits, for tests that prove what the database itself
  accepts or refuses. ledger_entries is append-only, so those rows stay; every test uses
  fresh UUIDs in its account names and refs so tests never see each other's rows.
"""

import asyncio
import sys
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    # Async psycopg can't run on Windows' default Proactor loop; Linux (CI, Docker) is unaffected.
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - only when no database is running
        await eng.dispose()
        pytest.skip(f"database not reachable: {exc.__class__.__name__}")
    yield eng
    await eng.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
