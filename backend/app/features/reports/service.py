"""Weekly report rules. Owner: James.

Every function takes the database session first and does NOT commit: the caller commits.
Day 4: the table, drafts and PDF rendering. Day 5 adds the report agent, review and sending.
"""

import uuid
from collections.abc import Sequence
from datetime import date, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.users.models import User
from app.core.errors import AppError
from app.features.projects import service as projects
from app.features.reports import pdf
from app.features.reports.models import Report, ReportStatus

MAX_BODY_CHARS = 20_000
MAX_EVIDENCE_IDS = 200


def week_start_of(day: date) -> date:
    """The Monday of the week `day` falls in."""
    return day - timedelta(days=day.weekday())


async def get_report(session: AsyncSession, report_id: uuid.UUID, *, lock: bool = False) -> Report:
    query = select(Report).where(Report.id == report_id)
    if lock:
        query = query.with_for_update()
    report = await session.scalar(query)
    if report is None:
        raise AppError("report_not_found", "Report not found.", 404)
    return report


async def create_draft(
    session: AsyncSession,
    project_id: uuid.UUID,
    week_start: date,
    body_md: str,
    evidence_ids: Sequence[uuid.UUID] = (),
    *,
    actor_id: uuid.UUID | None = None,
    request: Request | None = None,
) -> Report:
    """Save the week's draft (the report agent's `create_report_draft` tool). Re-drafting replaces it.

    - 404 project_not_found
    - 422 week_not_monday, report_empty, report_too_long, too_many_evidence_ids
    - 409 report_locked: this week's report was already reviewed or sent
    """
    await projects.get_project(session, project_id)
    if week_start.weekday() != 0:
        raise AppError("week_not_monday", "week_start must be a Monday.", 422)
    if not body_md.strip():
        raise AppError("report_empty", "The report has no text.", 422)
    if len(body_md) > MAX_BODY_CHARS:
        raise AppError("report_too_long", f"A report can be at most {MAX_BODY_CHARS} characters.", 422)
    if len(evidence_ids) > MAX_EVIDENCE_IDS:
        raise AppError("too_many_evidence_ids", f"A report can cite at most {MAX_EVIDENCE_IDS} items.", 422)

    report = await session.scalar(
        select(Report)
        .where(Report.project_id == project_id, Report.week_start == week_start)
        .with_for_update()
    )
    if report is not None and report.status != ReportStatus.DRAFT.value:
        raise AppError("report_locked", f"This week's report is already {report.status}.", 409)
    before = audit.snapshot(report) if report is not None else None
    if report is None:
        report = Report(project_id=project_id, week_start=week_start)
        session.add(report)
    report.body_md = body_md
    report.evidence_ids = list(dict.fromkeys(evidence_ids))  # keep order, drop repeats
    report.pdf_key = None  # any earlier PDF no longer matches the text
    await session.flush()
    await session.refresh(report)
    await audit.record(
        session, actor_id, "report.drafted", "report", report.id, before, audit.snapshot(report), request
    )
    return report


async def list_for_project(session: AsyncSession, user: User, project_id: uuid.UUID) -> list[Report]:
    """A project's reports, newest week first. Project members and ops (403 not_project_member)."""
    await projects.require_project_member(session, user, project_id)
    result = await session.scalars(
        select(Report).where(Report.project_id == project_id).order_by(Report.week_start.desc())
    )
    return list(result)


async def render_report_pdf(session: AsyncSession, report_id: uuid.UUID) -> bytes:
    """The report as a PDF, titled with the project's name. Raises OSError without WeasyPrint's libraries."""
    report = await get_report(session, report_id)
    project = await projects.get_project(session, report.project_id)
    return pdf.render_pdf(
        report.body_md, title=project.title, week_start=report.week_start, evidence_ids=report.evidence_ids
    )
