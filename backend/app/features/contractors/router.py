"""HTTP endpoints for contractor applications, vetting and the directory (ADR 0007). Owner: Christopher.

Routes are mounted under /api/v1 automatically. The public form needs no login; everything else is ops only.
Write endpoints accept an optional Idempotency-Key header.
"""

import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.base.users.models import User
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT
from app.features.contractors import applications, service
from app.features.contractors.models import ContractorApplicationStatus
from app.features.contractors.schemas import (
    ContractorApplicationCreated,
    ContractorApplicationIn,
    ContractorApplicationOut,
    ContractorApplicationPage,
    ContractorDecisionIn,
    ContractorOut,
    ContractorPage,
)

router = APIRouter(tags=["contractors"])

OpsUser = Annotated[User, Depends(users.require_role("ops"))]
Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]


@router.post("/contractor-applications", status_code=201, response_model=ContractorApplicationCreated)
async def apply_from_website(
    payload: ContractorApplicationIn, request: Request, session: SessionDep, key: IdempotencyKeyDep
) -> JSONResponse | ContractorApplicationCreated:
    """The form on /contractors. Public (no login), so it is rate limited per IP and has a honeypot."""
    if payload.website:  # a bot filled the hidden field: look like success, store nothing
        return ContractorApplicationCreated(id=uuid.uuid4(), status="pending")
    # The scope holds a hash of the phone, never the number itself.
    who = hashlib.sha256(payload.phone.strip().lower().encode()).hexdigest()[:32]
    scope = f"POST /contractor-applications {who}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    ip = request.client.host if request.client else "unknown"
    row = await applications.submit(session, payload, ip)
    body = ContractorApplicationCreated(id=row.id, status="pending").model_dump(mode="json")
    await remember(session, key, scope, 201, body)
    await session.commit()
    return JSONResponse(status_code=201, content=body)


@router.get("/contractor-applications", response_model=ContractorApplicationPage)
async def list_applications(
    session: SessionDep,
    _ops: OpsUser,
    status: Annotated[ContractorApplicationStatus, Query()] = ContractorApplicationStatus.PENDING,
    cursor: str | None = None,
    limit: Limit = DEFAULT_LIMIT,
) -> ContractorApplicationPage:
    """The queue: applications with this status (pending by default), oldest first."""
    rows, next_cursor = await service.list_applications(
        session, status=status.value, cursor=cursor, limit=limit
    )
    return ContractorApplicationPage.model_validate(
        {"items": rows, "next_cursor": next_cursor}, from_attributes=True
    )


@router.get("/contractor-applications/{application_id}", response_model=ContractorApplicationOut)
async def get_application(
    application_id: uuid.UUID, session: SessionDep, _ops: OpsUser
) -> ContractorApplicationOut:
    """One application in full, to check before deciding."""
    return ContractorApplicationOut.model_validate(await service.get_application(session, application_id))


@router.post("/contractor-applications/{application_id}/decision", response_model=ContractorApplicationOut)
async def decide(
    application_id: uuid.UUID,
    body: ContractorDecisionIn,
    request: Request,
    session: SessionDep,
    actor: OpsUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Approve (the required checks ticked, with a profile summary) or reject (with a reason)."""
    scope = f"POST /contractor-applications/{application_id}/decision {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    application = await service.decide(session, application_id, body, actor.id, request=request)
    out = ContractorApplicationOut.model_validate(application).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.get("/contractors", response_model=ContractorPage)
async def list_contractors(
    session: SessionDep,
    _ops: OpsUser,
    state: str | None = Query(default=None, max_length=60),
    specialty: str | None = Query(default=None, max_length=30),
    listed: bool | None = None,
    cursor: str | None = None,
    limit: Limit = DEFAULT_LIMIT,
) -> ContractorPage:
    """The directory of approved contractors; filter by state, specialty and whether they are listed."""
    rows, next_cursor = await service.list_contractors(
        session, state=state, specialty=specialty, listed=listed, cursor=cursor, limit=limit
    )
    return ContractorPage(items=[ContractorOut.model_validate(r) for r in rows], next_cursor=next_cursor)
