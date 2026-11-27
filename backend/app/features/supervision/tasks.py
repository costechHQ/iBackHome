"""Background jobs for supervision.

- supervision.notify_spot_check: queued after a spot check is scheduled and committed; tells the visiting
  supervisor (notices.send_assigned).
- supervision.send_application_emails: queued after a website application is saved and committed; emails ops
  and sends the applicant a receipt (applications.send_emails), retrying until both are out.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.features.supervision import applications, notices
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


RETRY_MINUTES = 10
MAX_RETRIES = 12  # about two hours of tries; the saved application is still there for ops either way


async def _send_application_emails(application_id: uuid.UUID) -> bool:
    async with _session() as session:
        return await applications.send_emails(session, application_id)


@celery_app.task(name="supervision.send_application_emails", bind=True, max_retries=MAX_RETRIES)  # type: ignore[untyped-decorator]
def send_application_emails_task(self, application_id: str) -> bool:  # type: ignore[no-untyped-def]
    """Email ops and the applicant. Safe to run twice (each email is marked when sent)."""
    if asyncio.run(_send_application_emails(uuid.UUID(application_id))):
        return True
    raise self.retry(countdown=RETRY_MINUTES * 60)
