"""Async database engine and session dependency.

Use in a router:

    from app.core.db import SessionDep

    @router.get("/things")
    async def list_things(session: SessionDep) -> ...:
        ...
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# Fail fast when the database is unreachable (otherwise a connect can hang for minutes and
# /healthz never answers). Seconds; libpq's connect_timeout.
CONNECT_TIMEOUT_SECONDS = 5

engine = create_async_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
