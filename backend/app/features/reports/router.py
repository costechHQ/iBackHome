"""HTTP endpoints for weekly reports. Owner: James.

Routes are mounted under /api/v1 automatically; the rules live in service.py.
"""

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.reports import service
from app.features.reports.models import Report
from app.features.reports.schemas import ReportOut

router = APIRouter(tags=["reports"])


def _out(report: Report) -> ReportOut:
    return ReportOut(
        id=report.id,
        project_id=report.project_id,
        week_start=report.week_start,
        status=report.status,
        body_md=report.body_md,
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
    return [_out(r) for r in await service.list_for_project(session, user, project_id)]


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
    out = _out(report).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)
