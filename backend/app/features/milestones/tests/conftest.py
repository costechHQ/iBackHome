"""Fixtures for milestone tests.

`db_session` runs each test inside a transaction against the real Postgres database
(DATABASE_URL) and rolls everything back afterwards, so tests never leave data behind.
Tests that need it are skipped when no database is reachable.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().database_url)
    try:
        connection = await engine.connect()
    except Exception as exc:  # pragma: no cover - only when no database is running
        await engine.dispose()
        pytest.skip(f"database not reachable: {exc.__class__.__name__}")
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()
