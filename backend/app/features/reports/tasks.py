"""Background jobs for weekly reports. Owner: James.

Spec (background jobs):
- reports.generate_weekly: Friday 16:00 WAT (Beat runs in UTC, so 15:00 UTC), the report agent per
  active project.
- reports.send_reviewed: every 15 minutes, sends reports marked reviewed.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.base.users import service as users
from app.core.config import get_settings
from app.core.errors import AppError
from app.features.agents import report_agent
from app.features.agents import service as agents
from app.features.projects import service as projects
from app.features.reports import service
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

celery_app.conf.beat_schedule["reports.generate_weekly"] = {
    "task": "reports.generate_weekly",
    "schedule": crontab(day_of_week="fri", hour=15, minute=0),  # 16:00 Africa/Lagos
}
celery_app.conf.beat_schedule["reports.send_reviewed"] = {
    "task": "reports.send_reviewed",
    "schedule": crontab(minute="*/15"),
}


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    # A fresh engine per run: each Celery task has its own event loop (same pattern as evidence/tasks.py).
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        await engine.dispose()


async def generate_all(session: AsyncSession, *, today: datetime | None = None) -> dict[str, int]:
    """Draft this week's report for every active project, committing each one on its own."""
    week_start = service.week_start_of((today or datetime.now(UTC)).date())
    agent = await users.get_user(session, agents.agent_user_id(report_agent.AGENT_NAME))
    if agent is None:
        log.error("reports.generate_weekly: the report agent's user isn't seeded; nothing drafted")
        return {"drafted": 0, "fallback": 0, "skipped": 0, "failed": 0}

    active, cursor = [], None
    while True:  # the agent is ops, so this lists every project
        page, cursor = await projects.list_projects(session, agent, cursor=cursor, limit=100)
        active += [p.id for p in page if p.status == "active"]
        if cursor is None:
            break

    counts = {"drafted": 0, "fallback": 0, "skipped": 0, "failed": 0}
    for project_id in active:
        try:
            outcome = await report_agent.generate_weekly_report(session, project_id, week_start)
            await session.commit()
        except AppError as exc:
            await session.rollback()
            if exc.code == "report_locked":  # already reviewed or sent this week: nothing to do
                counts["skipped"] += 1
                continue
            log.exception("reports.generate_weekly: project %s failed", project_id)
            counts["failed"] += 1
            continue
        except Exception:  # noqa: BLE001 - one project's failure must not stop the others
            await session.rollback()
            log.exception("reports.generate_weekly: project %s failed", project_id)
            counts["failed"] += 1
            continue
        counts["drafted" if outcome.used_model else "fallback"] += 1
    return counts


async def _generate() -> dict[str, int]:
    async with _session() as session:
        return await generate_all(session)


async def _send() -> int:
    async with _session() as session:
        sent = await service.send_reviewed(session)
        await session.commit()
        return sent


@celery_app.task(name="reports.generate_weekly")  # type: ignore[untyped-decorator]
def generate_weekly() -> dict[str, int]:
    """Friday's drafts: the report agent per active project. Safe to run twice (re-drafts this week)."""
    return asyncio.run(_generate())


@celery_app.task(name="reports.send_reviewed")  # type: ignore[untyped-decorator]
def send_reviewed() -> int:
    """Send every reviewed report. Safe to overlap: rows are locked with SKIP LOCKED."""
    return asyncio.run(_send())
