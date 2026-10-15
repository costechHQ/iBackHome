"""HTTP endpoints for evidence: devices, upload URLs and capture submission."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.base.users.models import User
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.evidence import service
from app.features.evidence.schemas import (
    DeviceIn,
    DeviceOut,
    EvidenceIn,
    EvidenceOut,
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
    actor: OpsUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    scope = f"POST /devices/{device_pk}/revoke {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    device = await service.revoke_device(session, device_pk)
    out = DeviceOut.model_validate(device).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.post("/evidence/upload-url", response_model=UploadUrlOut)
async def get_upload_url(body: UploadUrlRequest, session: SessionDep, actor: DeviceOwner) -> UploadUrlOut:
    """A 15-minute pre-signed URL to PUT one photo (JPEG, max 10 MB) or video (MP4, max 60 MB)."""
    return await service.create_upload_url(session, actor, body)


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
