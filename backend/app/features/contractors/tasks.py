"""Background jobs for contractor applications.

- contractors.send_application_emails: queued after an application is saved and committed; emails ops and
  sends the applicant a receipt (applications.send_emails), retrying until both are out.
- contractors.send_decision_email: queued after ops decide; tells the applicant the outcome.
- contractors.send_match_request_email / send_match_notice: match requests (ADR 0007, phase 2): ops are
  emailed the brief; the client and the contractor are told by notify(), once each.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.features.contractors import applications, match_notices
from app.workers.celery_app import celery_app

RETRY_MINUTES = 10
MAX_RETRIES = 12  # about two hours of tries; the saved application is still there for ops either way


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    # A fresh engine per run: each Celery task has its own event loop (as in supervision/tasks.py).
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        await engine.dispose()


async def _send_application_emails(application_id: uuid.UUID) -> bool:
    async with _session() as session:
        return await applications.send_emails(session, application_id)


async def _send_decision_email(application_id: uuid.UUID) -> bool:
    async with _session() as session:
        return await applications.send_decision_email(session, application_id)


@celery_app.task(name="contractors.send_application_emails", bind=True, max_retries=MAX_RETRIES)  # type: ignore[untyped-decorator]
def send_application_emails_task(self, application_id: str) -> bool:  # type: ignore[no-untyped-def]
    """Email ops and the applicant. Safe to run twice (each email is marked when sent)."""
    if asyncio.run(_send_application_emails(uuid.UUID(application_id))):
        return True
    raise self.retry(countdown=RETRY_MINUTES * 60)


@celery_app.task(name="contractors.send_decision_email", bind=True, max_retries=MAX_RETRIES)  # type: ignore[untyped-decorator]
def send_decision_email_task(self, application_id: str) -> bool:  # type: ignore[no-untyped-def]
    """Tell the applicant the decision. Safe to run twice."""
    if asyncio.run(_send_decision_email(uuid.UUID(application_id))):
        return True
    raise self.retry(countdown=RETRY_MINUTES * 60)


async def _send_match_request_email(request_id: uuid.UUID) -> bool:
    async with _session() as session:
        return await match_notices.send_ops_email(session, request_id)


async def _send_match_notice(request_id: uuid.UUID, kind: str) -> None:
    async with _session() as session:
        await match_notices.send_notice(session, request_id, kind)
        await session.commit()


@celery_app.task(name="contractors.send_match_request_email", bind=True, max_retries=MAX_RETRIES)  # type: ignore[untyped-decorator]
def send_match_request_email_task(self, request_id: str) -> bool:  # type: ignore[no-untyped-def]
    """Email ops the brief of a new match request. Safe to run twice (marked when sent)."""
    if asyncio.run(_send_match_request_email(uuid.UUID(request_id))):
        return True
    raise self.retry(countdown=RETRY_MINUTES * 60)


@celery_app.task(name="contractors.send_match_notice")  # type: ignore[untyped-decorator]
def send_match_notice_task(request_id: str, kind: str) -> None:
    """Tell the client (shortlist ready) or the contractor (chosen). Safe to run twice: keyed sends."""
    asyncio.run(_send_match_notice(uuid.UUID(request_id), kind))
