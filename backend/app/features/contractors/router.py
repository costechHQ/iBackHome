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
from app.features.contractors import applications, matching, service
from app.features.contractors.models import ContractorApplicationStatus, MatchStatus
from app.features.contractors.schemas import (
    ContractorApplicationCreated,
    ContractorApplicationIn,
    ContractorApplicationOut,
    ContractorApplicationPage,
    ContractorDecisionIn,
    ContractorOut,
    ContractorPage,
    MatchCancelIn,
    MatchChooseIn,
    MatchRequestIn,
    MatchRequestOut,
    MatchRequestPage,
    MatchShortlistIn,
)

router = APIRouter(tags=["contractors"])

OpsUser = Annotated[User, Depends(users.require_role("ops"))]
ClientUser = Annotated[User, Depends(users.require_role("client"))]
ClientOrOps = Annotated[User, Depends(users.require_role("client", "ops"))]
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


# --- Match requests (ADR 0007, phase 2) ---------------------------------------------------------------


@router.post("/projects/{project_id}/match-request", status_code=201, response_model=MatchRequestOut)
async def request_match(
    project_id: uuid.UUID,
    body: MatchRequestIn,
    request: Request,
    session: SessionDep,
    client: ClientUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """The project's client asks ops to find them a contractor (a draft project with none yet)."""
    scope = f"POST /projects/{project_id}/match-request {client.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    row = await matching.request_match(session, client, project_id, body, request=request)
    out = (await matching.view(session, row)).model_dump(mode="json")
    await remember(session, key, scope, 201, out)
    await session.commit()
    return JSONResponse(status_code=201, content=out)


@router.get("/projects/{project_id}/match-request", response_model=MatchRequestOut)
async def get_match_request(project_id: uuid.UUID, session: SessionDep, user: ClientOrOps) -> MatchRequestOut:
    """The project's latest request and, once shortlisted, the shortlist as client-safe cards."""
    row = await matching.get_for_project(session, user, project_id)
    return await matching.view(session, row)


@router.post("/match-requests/{request_id}/choose", response_model=MatchRequestOut)
async def choose(
    request_id: uuid.UUID,
    body: MatchChooseIn,
    request: Request,
    session: SessionDep,
    client: ClientUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Choose one shortlisted contractor: they are set on the project and told."""
    scope = f"POST /match-requests/{request_id}/choose {client.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    row = await matching.choose(session, request_id, body.contractor_id, client, request=request)
    out = (await matching.view(session, row)).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.post("/match-requests/{request_id}/cancel", response_model=MatchRequestOut)
async def cancel(
    request_id: uuid.UUID,
    body: MatchCancelIn,
    request: Request,
    session: SessionDep,
    user: ClientOrOps,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """The client who made the request, or ops, cancels an open or shortlisted request."""
    scope = f"POST /match-requests/{request_id}/cancel {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    row = await matching.cancel(session, request_id, body.reason, user, request=request)
    out = (await matching.view(session, row)).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.get("/ops/match-requests", response_model=MatchRequestPage)
async def list_match_requests(
    session: SessionDep,
    _ops: OpsUser,
    status: Annotated[MatchStatus, Query()] = MatchStatus.OPEN,
    cursor: str | None = None,
    limit: Limit = DEFAULT_LIMIT,
) -> MatchRequestPage:
    """The queue: requests with this status (open by default), oldest first."""
    items, next_cursor = await matching.list_requests(session, status=status, cursor=cursor, limit=limit)
    return MatchRequestPage(items=items, next_cursor=next_cursor)


@router.post("/match-requests/{request_id}/shortlist", response_model=MatchRequestOut)
async def set_shortlist(
    request_id: uuid.UUID,
    body: MatchShortlistIn,
    request: Request,
    session: SessionDep,
    actor: OpsUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Ops put 1 to 3 approved contractors forward (or replace the list); the client is told."""
    scope = f"POST /match-requests/{request_id}/shortlist {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    row = await matching.shortlist(
        session, request_id, body.contractor_ids, body.note, actor, request=request
    )
    out = (await matching.view(session, row)).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)
