"""HTTP endpoints for weekly reports. Owner: James.

Routes are mounted under /api/v1 automatically; the rules live in service.py.
"""

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.reports import service
from app.features.reports.models import Report
from app.features.reports.schemas import PersonRef, ReportNoteIn, ReportOut

router = APIRouter(tags=["reports"])


async def _ref(session: AsyncSession, user_id: uuid.UUID | None) -> PersonRef | None:
    """The id and name of a person named on the report (never their phone or email)."""
    if user_id is None:
        return None
    person = await users.get_user(session, user_id)
    return PersonRef(id=person.id, full_name=person.full_name) if person else None


async def _out(session: AsyncSession, report: Report) -> ReportOut:
    return ReportOut(
        id=report.id,
        project_id=report.project_id,
        week_start=report.week_start,
        status=report.status,
        body_md=report.body_md,
        supervisor_note=report.supervisor_note,
        note_by=await _ref(session, report.note_by),
        reviewed_by=await _ref(session, report.reviewed_by),
        evidence_ids=report.evidence_ids,
        pdf_url=service.pdf_url(report),
        sent_at=report.sent_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get("/projects/{project_id}/reports", response_model=list[ReportOut])
async def list_reports(
    project_id: uuid.UUID, session: SessionDep, user: users.CurrentUserDep
) -> list[ReportOut]:
    """A project's weekly reports, newest first (its client, contractor, supervisor, or ops)."""
    return [await _out(session, r) for r in await service.list_for_project(session, user, project_id)]


@router.patch("/reports/{report_id}", response_model=ReportOut)
async def set_report_note(
    report_id: uuid.UUID,
    body: ReportNoteIn,
    request: Request,
    session: SessionDep,
    user: users.CurrentUserDep,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Add, change or remove your note on a draft report (the project's supervisor or ops).

    The note is shown under your name and goes out with the report. The AI's text is never changed.
    """
    scope = f"PATCH /reports/{report_id} {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    report = await service.set_note(session, report_id, user, body.supervisor_note, request=request)
    out = (await _out(session, report)).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.post("/reports/{report_id}/review", response_model=ReportOut)
async def review_report(
    report_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    user: users.CurrentUserDep,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """The project's supervisor (or ops) approves the draft; its PDF is made and it is queued to send."""
    scope = f"POST /reports/{report_id}/review {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    report = await service.review(session, report_id, user, request=request)
    out = (await _out(session, report)).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)
