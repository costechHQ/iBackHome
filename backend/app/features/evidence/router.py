"""HTTP endpoints for evidence: devices, upload URLs and capture submission."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.base.users.models import User
from app.core import pagination
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.evidence import service
from app.features.evidence.schemas import (
    DecisionIn,
    DeviceIn,
    DeviceOut,
    EvidenceIn,
    EvidenceOut,
    GalleryItem,
    GalleryPage,
    UploadUrlOut,
    UploadUrlRequest,
)

router = APIRouter(tags=["evidence"])

DeviceOwner = Annotated[User, Depends(users.require_role("supervisor", "contractor"))]
OpsUser = Annotated[User, Depends(users.require_role("ops"))]


@router.post("/devices", status_code=201, response_model=DeviceOut)
async def register_device(
    body: DeviceIn,
    session: SessionDep,
    actor: DeviceOwner,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    scope = f"POST /devices {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    device, created = await service.register_device(session, actor.id, body.device_id, body.public_key)
    out = DeviceOut.model_validate(device).model_dump(mode="json")
    status = 201 if created else 200
    await remember(session, key, scope, status, out)
    await session.commit()
    return JSONResponse(status_code=status, content=out)


@router.post("/devices/{device_pk}/revoke", response_model=DeviceOut)
async def revoke_device(
    device_pk: uuid.UUID,
    session: SessionDep,
    actor: DeviceOwner,
    request: Request,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    scope = f"POST /devices/{device_pk}/revoke {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    device = await service.revoke_device(session, actor, device_pk, request)
    out = DeviceOut.model_validate(device).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.post("/evidence/upload-url", response_model=UploadUrlOut)
async def get_upload_url(
    body: UploadUrlRequest, session: SessionDep, actor: DeviceOwner, key: IdempotencyKeyDep
) -> JSONResponse:
    """A 15-minute pre-signed URL to PUT one photo (JPEG, max 10 MB) or video (MP4, max 60 MB)."""
    scope = f"POST /evidence/upload-url {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    out = (await service.create_upload_url(session, actor, body)).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.post("/evidence", status_code=201, response_model=EvidenceOut)
async def submit_evidence(
    body: EvidenceIn,
    request: Request,
    session: SessionDep,
    actor: DeviceOwner,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Save a capture's metadata and signature once the file is uploaded; checks run in the background."""
    scope = f"POST /evidence {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    evidence, created = await service.submit_evidence(session, actor, body, request)
    out = EvidenceOut.model_validate(evidence).model_dump(mode="json")
    status = 201 if created else 200
    await remember(session, key, scope, status, out)
    await session.commit()
    if created:
        service.enqueue_run_checks(evidence.id)  # after the commit, so the job finds the row
    return JSONResponse(status_code=status, content=out)


@router.get("/projects/{project_id}/evidence", response_model=GalleryPage)
async def evidence_gallery(
    project_id: uuid.UUID,
    session: SessionDep,
    user: users.CurrentUserDep,
    milestone_id: uuid.UUID | None = None,
    status: Literal["pending_checks", "accepted", "flagged", "rejected"] | None = None,
    kind: Literal["photo", "video"] | None = None,
    captured_by_role: Literal["supervisor", "contractor"] | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=pagination.MAX_LIMIT)] = pagination.DEFAULT_LIMIT,
) -> GalleryPage:
    """The project's photos and videos with 15-minute view links. Clients see accepted ones, EXIF-free."""
    entries, next_cursor = await service.list_gallery(
        session,
        user,
        project_id,
        milestone_id=milestone_id,
        status=status,
        kind=kind,
        captured_by_role=captured_by_role,
        cursor=cursor,
        limit=limit,
    )
    items = [
        GalleryItem(
            **EvidenceOut.model_validate(e.evidence).model_dump(),
            read_url=e.read_url,
            read_url_expires_in=service.READ_URL_TTL_S,
            is_client_copy=e.is_client_copy,
        )
        for e in entries
    ]
    return GalleryPage(items=items, next_cursor=next_cursor)


@router.post("/evidence/{evidence_id}/decision", response_model=EvidenceOut)
async def decide_evidence(
    evidence_id: uuid.UUID,
    body: DecisionIn,
    request: Request,
    session: SessionDep,
    ops: OpsUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Ops: accept or reject evidence the server flagged. Rejecting needs notes."""
    scope = f"POST /evidence/{evidence_id}/decision {ops.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    evidence = await service.decide_flagged(session, ops, evidence_id, body.decision, body.notes, request)
    out = EvidenceOut.model_validate(evidence).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)
