"""Background jobs for milestones.

- milestones.send_update: queued after a claimed, verified, rejected or released move commits;
  messages the people involved (notices.send_update).
- milestones.remind: daily 09:00 WAT (08:00 UTC); reminds clients of milestones waiting over 48 h
  for approval and supervisors of claims waiting over 24 h (notices.send_reminders).
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.features.milestones import notices
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

celery_app.conf.beat_schedule["milestones.remind"] = {
    "task": "milestones.remind",
    "schedule": crontab(hour=8, minute=0),  # 09:00 Africa/Lagos
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


async def _send_update(milestone_id: uuid.UUID, event: str, key: str) -> int:
    async with _session() as session:
        rows = await notices.send_update(session, milestone_id, event, key)
        await session.commit()
        return len(rows)


async def _remind() -> dict[str, int]:
    async with _session() as session:
        counts = await notices.send_reminders(session)
        await session.commit()
        return counts


@celery_app.task(name="milestones.send_update")  # type: ignore[untyped-decorator]
def send_update_task(milestone_id: str, event: str, key: str) -> int:
    """Message the people involved in one milestone move. Safe to run twice (each send has a key)."""
    return asyncio.run(_send_update(uuid.UUID(milestone_id), event, key))


@celery_app.task(name="milestones.remind")  # type: ignore[untyped-decorator]
def remind() -> dict[str, int]:
    """Daily reminders. Safe to run twice a day: one reminder per milestone per day."""
    counts = asyncio.run(_remind())
    log.info("milestones.remind: %s", counts)
    return counts
