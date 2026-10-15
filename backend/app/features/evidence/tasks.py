"""Background jobs for evidence. Owner: Abigail."""

import asyncio
import logging
import random
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.errors import AppError
from app.features.evidence import checks
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

MAX_RETRIES = 6
RETRY_BASE_S = 30
RETRY_MAX_S = 15 * 60


def retry_delay(retries: int) -> float:
    """Seconds before the next try: 30 s, 1 min, 2 min ... capped at 15 min, with a little jitter."""
    wait = float(min(RETRY_BASE_S * 2**retries, RETRY_MAX_S))
    return wait * random.uniform(0.75, 1.0)  # noqa: S311


async def _with_session[T](work: Callable[[AsyncSession], Awaitable[T]]) -> T:
    # A fresh engine per run: each Celery task gets its own event loop, and pooled connections
    # cannot be shared across loops.
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await work(session)
            await session.commit()
            return result
    finally:
        await engine.dispose()


async def _run(evidence_id: uuid.UUID) -> str:
    async def work(session: AsyncSession) -> str:
        return (await checks.run_checks(session, evidence_id)).status

    return await _with_session(work)


async def _flag_unchecked(evidence_id: uuid.UUID, reason: str) -> str:
    async def work(session: AsyncSession) -> str:
        return (await checks.flag_unchecked(session, evidence_id, reason)).status

    return str(await _with_session(work))


@celery_app.task(name="evidence.run_checks", bind=True, max_retries=MAX_RETRIES)  # type: ignore[untyped-decorator]
def run_checks(self, evidence_id: str) -> str:  # type: ignore[no-untyped-def]
    """Run the server checks on one capture and save accepted, flagged or rejected.

    Takes an id, never an object, and is safe to run twice: a capture that is no longer
    `pending_checks` is left alone. If storage or the database is briefly down the run is retried
    with growing waits; if it still cannot run, the capture is flagged for ops rather than left
    waiting forever.
    """
    target = uuid.UUID(evidence_id)
    try:
        return asyncio.run(_run(target))
    except AppError:
        raise  # a real answer (for example "not found"), not an outage
    except Exception as exc:
        if self.request.retries < self.max_retries:
            log.warning("evidence %s: checks could not run (%r); retrying", evidence_id, exc)
            raise self.retry(exc=exc, countdown=retry_delay(self.request.retries)) from exc
        log.exception("evidence %s: checks kept failing; flagging for ops", evidence_id)
        return asyncio.run(
            _flag_unchecked(
                target, "The automatic checks could not run after several tries; ops must review."
            )
        )
