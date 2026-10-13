"""Commit-capable fixtures for the payments tests that must really commit.

Why real commits: the ledger balance check is a DEFERRABLE INITIALLY DEFERRED constraint trigger,
so Postgres only runs it at COMMIT. The shared `db_session` (backend/conftest.py) never commits;
its session.commit() only releases a savepoint, so the trigger never fires there. Tests that prove
what the database itself accepts or refuses (unbalanced or mixed-currency writes, the append-only
guards, "post_transaction does not commit") therefore use `engine` / `session_factory` below.
Every other payments test uses the shared, rolled-back `db_session`.

Rows left behind: ledger_entries is append-only. UPDATE, DELETE and TRUNCATE are refused by
trigger for every role (superuser included) and revoked from the app role, so committed test
rows cannot be cleaned up. They are kept harmless instead: every committed row has a fresh
uuid4 `ref_id` and tests look rows up only by that ref; the fixed accounts they post to use the
`raw:` prefix, which no production code and no other test reads. Rejected transactions leave
nothing, because the database refuses the commit.

If the database is unreachable, `engine` fails in CI and skips only locally, the same rule as
backend/conftest.py.
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.db import CONNECT_TIMEOUT_SECONDS


@pytest.fixture
async def engine(migrated_database: None) -> AsyncIterator[AsyncEngine]:
    """Engine whose connections commit for real, against the database migrated to head."""
    eng = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )
    try:
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any failure here means "no usable database"
        await eng.dispose()
        if os.environ.get("CI"):
            pytest.fail(f"database required in CI: {exc.__class__.__name__}")
        pytest.skip(f"database not reachable: {exc.__class__.__name__}")
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sessions that commit for real (see the module docstring)."""
    return async_sessionmaker(engine, expire_on_commit=False)
