"""Background jobs for notifications. 

- notifications.retry_failed: every 10 minutes, sends again every message that failed on all
  channels (spec: "Background jobs and notifications").
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.base.notifications import service
from app.core.config import get_settings
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

celery_app.conf.beat_schedule["notifications.retry_failed"] = {
    "task": "notifications.retry_failed",
    "schedule": crontab(minute="*/10"),
}


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    # A fresh engine per run: each Celery task has its own event loop (as in evidence/tasks.py).
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        await engine.dispose()


async def _retry() -> dict[str, int]:
    async with _session() as session:
        counts = await service.retry_failed(session)
        await session.commit()
        return counts


@celery_app.task(name="notifications.retry_failed")  # type: ignore[untyped-decorator]
def retry_failed() -> dict[str, int]:
    """Retry failed messages. Safe to overlap: rows are locked with SKIP LOCKED."""
    counts = asyncio.run(_retry())
    if counts["sent"] or counts["failed"]:
        log.info("notifications.retry_failed: %s", counts)
    return counts
