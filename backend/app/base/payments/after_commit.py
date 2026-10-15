"""Run a callback only once the current database transaction has committed. Owner: Gabriel.

Money jobs (submit a release, send a payout) are queued for Celery from inside a transaction the
caller commits later. Queued straight away, the worker could start before the row it needs is
committed, or run for a transaction that is then rolled back. Instead:

    from app.base.payments.after_commit import after_commit

    after_commit(session, enqueue_submit_release, release.id)   # runs after session.commit()

A rollback drops the callbacks. A callback that raises is logged and swallowed: the commit has
already happened, and the Beat sweeper (escrow.sweep) picks up anything that was never queued.
"""

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, SessionTransaction

logger = logging.getLogger(__name__)

_KEY = "payments_after_commit"


def after_commit(session: AsyncSession, callback: Callable[..., Any], *args: Any) -> None:
    sync = session.sync_session
    if not sync.in_transaction():
        sync.begin()  # so a rollback before any query still drops the callback (no I/O here)
    sync.info.setdefault(_KEY, []).append((callback, args))


@event.listens_for(Session, "after_commit")
def _run_callbacks(session: Session) -> None:
    for callback, args in session.info.pop(_KEY, []):
        try:
            callback(*args)
        except Exception:
            logger.exception("after-commit callback %s failed", getattr(callback, "__name__", callback))


@event.listens_for(Session, "after_soft_rollback")
def _drop_callbacks(session: Session, previous_transaction: SessionTransaction) -> None:
    # Only the outermost transaction: a savepoint that failed and was caught (begin_nested) must
    # not drop the work queued earlier in the same transaction.
    if previous_transaction.parent is None:
        session.info.pop(_KEY, None)
