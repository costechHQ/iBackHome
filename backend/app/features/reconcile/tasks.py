"""The nightly reconciliation job. Owner: James.

Spec (background jobs): `payments.reconcile`, daily 02:00 (Africa/Lagos; Beat runs in UTC, so 01:00 UTC).
It checks the whole previous UTC day, so every webhook for that day has had hours to arrive.
"""

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any

from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.features.reconcile import service
from app.features.reconcile.sources import default_sources
from app.workers.celery_app import celery_app

celery_app.conf.beat_schedule["payments.reconcile"] = {
    "task": "payments.reconcile",
    "schedule": crontab(hour=1, minute=0),  # 02:00 Africa/Lagos
}


async def _run(day: date) -> dict[str, Any]:
    # A fresh engine per run: each Celery task has its own event loop (same pattern as evidence/tasks.py).
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            stripe, paystack, escrow = default_sources(session)
            result = await service.reconcile_day(session, day, stripe, paystack, escrow)
            await session.commit()
    finally:
        await engine.dispose()
    return {
        "day": day.isoformat(),
        "checked": result.checked,
        "unchecked": result.unchecked,
        "differences": len(result.differences),
    }


@celery_app.task(name="payments.reconcile")  # type: ignore[untyped-decorator]
def reconcile(day: str | None = None) -> dict[str, Any]:
    """Reconcile one UTC day (default: yesterday). Read-only towards money; writes audit entries only."""
    target = date.fromisoformat(day) if day else datetime.now(UTC).date() - timedelta(days=1)
    return asyncio.run(_run(target))
