"""Background jobs for escrow. Owner: Gabriel.

- escrow.submit_release (spec): send one release to the escrow partner; 3 retries with backoff
  while the partner is unreachable, then the release is `failed` and ops are alerted.
- escrow.sweep (every 5 minutes; not in the spec yet): re-queue releases left `requested` and
  payouts left unsent (a lost queue message, a dead worker). Both jobs are safe to run twice.

The work is an `async def` taking a session factory, so tests run it on their own session.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import payments
from app.base.payments.service import enqueue_send_transfer
from app.base.payments.tasks import Outcome, SessionFactory, in_session, retry_delay, worker_session
from app.core.errors import AppError
from app.features.escrow import service
from app.features.escrow.providers import EscrowProviderError
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

SUBMIT_RETRIES = 3  # spec: "retries 3 times with backoff, then alerts ops"
UNSENT_PAYOUT_AFTER = timedelta(minutes=10)


async def run_submit_release(
    factory: SessionFactory, release_id: uuid.UUID, retries: int, max_retries: int = SUBMIT_RETRIES
) -> Outcome:
    """One try of escrow.submit_release: "done", "retry" (partner unreachable, tries left) or
    "gave_up" (the release is now `failed` and ops are alerted)."""

    async def submit(session: AsyncSession) -> None:
        await service.submit_release(session, release_id)

    try:
        await in_session(factory, submit)
        return "done"
    except EscrowProviderError:
        if retries < max_retries:
            logger.warning("release %s: escrow partner unavailable; retrying", release_id)
            return "retry"
        reason = f"The escrow partner could not be reached after {retries + 1} tries."
    except AppError as exc:  # the partner refused (e.g. ref conflict, insufficient funds): no retry
        reason = f"The escrow partner refused the release: {exc.message}"

    async def fail(session: AsyncSession) -> None:
        await service.fail_release(session, release_id, reason)

    await in_session(factory, fail)
    return "gave_up"


@celery_app.task(name="escrow.submit_release", bind=True, max_retries=SUBMIT_RETRIES)  # type: ignore[untyped-decorator]
def submit_release_task(self, release_id: str) -> str:  # type: ignore[no-untyped-def]
    """Send a release to the escrow partner. Takes an id; the release id is the partner's
    idempotency ref, and a release that is no longer requested/submitted is left alone."""
    outcome = asyncio.run(run_submit_release(worker_session, uuid.UUID(release_id), self.request.retries))
    if outcome == "retry":
        raise self.retry(countdown=retry_delay(self.request.retries))
    return outcome


async def run_sweep(factory: SessionFactory, now: datetime | None = None) -> tuple[int, int]:
    """Re-queue stale releases and unsent payouts; returns how many of each."""
    now = now or datetime.now(UTC)

    async def find(session: AsyncSession) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
        releases = await service.list_stale_requests(session, now)
        unsent = await payments.list_unsent_payouts(session, now - UNSENT_PAYOUT_AFTER)
        return releases, unsent

    releases, unsent = await in_session(factory, find)
    for release_id in releases:
        service.enqueue_submit_release(release_id)
    for payout_id in unsent:
        enqueue_send_transfer(payout_id)
    if releases or unsent:
        logger.warning("sweep re-queued %s releases and %s payouts", len(releases), len(unsent))
    return len(releases), len(unsent)


@celery_app.task(name="escrow.sweep")  # type: ignore[untyped-decorator]
def sweep_task() -> list[int]:
    return list(asyncio.run(run_sweep(worker_session)))


celery_app.conf.beat_schedule["escrow.sweep"] = {"task": "escrow.sweep", "schedule": crontab(minute="*/5")}
