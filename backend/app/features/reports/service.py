"""Weekly report rules. Owner: James.

Every function takes the database session first and does NOT commit: the caller commits.
Status moves only forward: draft -> reviewed (supervisor or ops) -> sent (the 15-minute job).
The report agent itself is agents/report_agent.py.
"""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, date, datetime, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.users.models import Role, User
from app.core.errors import AppError
from app.features.projects import service as projects
from app.features.projects.models import Project
from app.features.reports import pdf, storage
from app.features.reports.models import Report, ReportStatus

log = logging.getLogger(__name__)

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


async def review(
    session: AsyncSession, report_id: uuid.UUID, user: User, *, request: Request | None = None
) -> Report:
    """Mark a draft reviewed and store its PDF; the 15-minute job then sends it.

    Reviewers: the project's assigned supervisor (spec) or ops (decided 2026-10-15, pending Christopher).
    - 404 report_not_found, 403 not_report_reviewer
    - 409 invalid_transition: the report isn't a draft
    - 503 pdf_unavailable: the PDF couldn't be made (nothing is changed)
    """
    report = await get_report(session, report_id, lock=True)
    project = await projects.get_project(session, report.project_id)
    if user.role != Role.OPS.value and user.id != project.supervisor_id:
        raise AppError(
            "not_report_reviewer", "Only the project's supervisor or ops can review a report.", 403
        )
    if report.status != ReportStatus.DRAFT.value:
        raise AppError("invalid_transition", f"A {report.status} report can't be reviewed.", 409)

    try:
        document = pdf.render_pdf(
            report.body_md,
            title=project.title,
            week_start=report.week_start,
            evidence_ids=report.evidence_ids,
        )
        key = storage.pdf_key(report.project_id, report.week_start)
        await asyncio.to_thread(storage.put_pdf, key, document)
    except Exception as exc:  # noqa: BLE001 - missing Pango (OSError) or storage down: refuse, change nothing
        log.exception("report %s: PDF not made", report.id)
        raise AppError("pdf_unavailable", "The report PDF couldn't be made. Try again shortly.", 503) from exc

    before = audit.snapshot(report)
    report.status = ReportStatus.REVIEWED.value
    report.pdf_key = key
    await session.flush()
    await session.refresh(report)
    await audit.record(
        session, user.id, "report.reviewed", "report", report.id, before, audit.snapshot(report), request
    )
    return report


def pdf_url(report: Report) -> str | None:
    """A 15-minute link to the report's PDF, once it has one."""
    return storage.presign_read(report.pdf_key) if report.pdf_key else None


# Sends one report; True only when it was really delivered.
Sender = Callable[[AsyncSession, Report, Project], Awaitable[bool]]


async def notify_client(session: AsyncSession, report: Report, project: Project) -> bool:
    """Tell the client their report is ready, through Lilian's notify() (spec: WhatsApp + email).

    STUB until base/notifications has notify(session, user_id, template, data, channels=None) on main:
    returns False, so reports stay `reviewed` and are sent by a later run instead of being marked
    sent without a message.
    """
    from app.base.notifications import service as notifications

    notify = getattr(notifications, "notify", None)
    if notify is None:
        log.warning("notifications.notify() isn't on main yet; report %s stays reviewed", report.id)
        return False
    data = {
        "report_id": str(report.id),
        "project_id": str(project.id),
        "project_title": project.title,
        "week_start": report.week_start.isoformat(),
    }
    await notify(session, project.client_id, "weekly_report_ready", data)
    return True


async def send_reviewed(session: AsyncSession, sender: Sender = notify_client) -> int:
    """Send every reviewed report; each one delivered becomes `sent`. Returns how many were sent.

    A failure on one report is logged and leaves it `reviewed` for the next run; it never blocks the rest.
    """
    waiting = list(
        await session.scalars(
            select(Report)
            .where(Report.status == ReportStatus.REVIEWED.value)
            .order_by(Report.created_at)
            .with_for_update(skip_locked=True)  # two overlapping runs never send the same report
        )
    )
    sent = 0
    for report in waiting:
        project = await projects.get_project(session, report.project_id)
        try:
            delivered = await sender(session, report, project)
        except Exception:  # noqa: BLE001 - one bad report must not stop the others
            log.exception("report %s: sending failed", report.id)
            continue
        if not delivered:
            continue
        before = audit.snapshot(report)
        report.status = ReportStatus.SENT.value
        report.sent_at = datetime.now(UTC)
        await session.flush()
        await session.refresh(report)
        await audit.record(session, None, "report.sent", "report", report.id, before, audit.snapshot(report))
        sent += 1
    return sent
