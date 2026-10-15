"""Background jobs for evidence. Owner: Abigail."""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.features.evidence import checks
from app.workers.celery_app import celery_app


async def _run(evidence_id: uuid.UUID) -> str:
    # A fresh engine per run: each Celery task gets its own event loop, and pooled connections
    # cannot be shared across loops.
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            evidence = await checks.run_checks(session, evidence_id)
            await session.commit()
            return evidence.status
    finally:
        await engine.dispose()


@celery_app.task(name="evidence.run_checks")  # type: ignore[untyped-decorator]
def run_checks(evidence_id: str) -> str:
    """Run the server checks on one capture and save accepted, flagged or rejected.

    Takes an id, never an object, and is safe to run twice: a capture that is no longer
    `pending_checks` is left alone.
    """
    return asyncio.run(_run(uuid.UUID(evidence_id)))
