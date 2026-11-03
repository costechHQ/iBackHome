"""Background jobs for supervision.

- supervision.notify_spot_check: queued after a spot check is scheduled and committed; tells the visiting
  supervisor (notices.send_assigned).
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.features.supervision import notices
from app.workers.celery_app import celery_app


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    # A fresh engine per run: each Celery task has its own event loop (as in milestones/tasks.py).
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        await engine.dispose()


async def _notify(spot_check_id: uuid.UUID) -> int:
    async with _session() as session:
        rows = await notices.send_assigned(session, spot_check_id)
        await session.commit()
        return len(rows)


@celery_app.task(name="supervision.notify_spot_check")  # type: ignore[untyped-decorator]
def notify_spot_check_task(spot_check_id: str) -> int:
    """Message the visiting supervisor. Safe to run twice (each send has a key)."""
    return asyncio.run(_notify(uuid.UUID(spot_check_id)))
