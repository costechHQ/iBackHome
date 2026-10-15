"""Background jobs for payments. Owner: Gabriel.

payments.send_transfer: send one queued payout to Paystack (see service.queue_transfer).

The Celery wrappers stay thin: the work is an `async def` that takes a session factory, so tests
run it on their own rolled-back session, and the retry decision is a plain function.
"""

import asyncio
import logging
import random
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.base import audit
from app.base.payments import service
from app.core.config import get_settings
from app.core.errors import AppError
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
Outcome = Literal["done", "retry", "gave_up"]

SEND_TRANSFER_RETRIES = 5
RETRY_BASE_S = 30
RETRY_MAX_S = 10 * 60


@asynccontextmanager
async def worker_session() -> AsyncIterator[AsyncSession]:
    """A session on a fresh engine: each Celery task runs its own event loop, and pooled
    connections cannot be shared across loops."""
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        await engine.dispose()


def retry_delay(retries: int) -> float:
    """Seconds before the next try: 30 s, 60 s, 120 s ... capped at 10 min, with a little jitter."""
    wait = float(min(RETRY_BASE_S * 2**retries, RETRY_MAX_S))
    return wait * random.uniform(0.75, 1.0)  # noqa: S311 - jitter, not security


async def in_session[T](factory: SessionFactory, work: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Run `work` in one transaction and commit it."""
    async with factory() as session:
        result = await work(session)
        await session.commit()
        return result


async def run_send_transfer(
    factory: SessionFactory, payout_id: uuid.UUID, retries: int, max_retries: int = SEND_TRANSFER_RETRIES
) -> Outcome:
    """One try of payments.send_transfer. "retry" while Paystack is unreachable and tries are left;
    then an ops alert (the payout stays pending without a transfer code, and the sweeper tries again)."""

    async def work(session: AsyncSession) -> None:
        await service.send_transfer(session, payout_id)

    try:
        await in_session(factory, work)
        return "done"
    except AppError as exc:
        if exc.code != "paystack_unavailable":
            raise
        if retries < max_retries:
            logger.warning("payout %s: Paystack unavailable; retrying", payout_id)
            return "retry"

    async def alert(session: AsyncSession) -> None:
        await audit.record(
            session,
            None,
            "payout.send_failed",
            "payout",
            payout_id,
            after={"reason": "Paystack could not be reached", "tries": retries + 1},
        )

    await in_session(factory, alert)
    logger.error("OPS ALERT: payout %s could not be sent after %s tries", payout_id, retries + 1)
    return "gave_up"


@celery_app.task(name="payments.send_transfer", bind=True, max_retries=SEND_TRANSFER_RETRIES)  # type: ignore[untyped-decorator]
def send_transfer_task(self, payout_id: str) -> str:  # type: ignore[no-untyped-def]
    """Send a queued payout to Paystack. Takes an id; safe to run twice (Paystack is idempotent on
    our reference, and a payout that already has a transfer code is left alone)."""
    outcome = asyncio.run(run_send_transfer(worker_session, uuid.UUID(payout_id), self.request.retries))
    if outcome == "retry":
        raise self.retry(countdown=retry_delay(self.request.retries))
    return outcome
