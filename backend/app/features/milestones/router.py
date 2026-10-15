"""HTTP endpoints for milestones.

- POST /milestones/{id}/claim    contractor: the work is done
- POST /milestones/{id}/verify   assigned supervisor: verified with a checklist, or rejected with a reason
- POST /milestones/{id}/approve  client: approve and ask escrow to release the money
- GET  /projects/{id}/milestones the project's milestones, for its members and ops
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.base.audit.actor import CurrentActor
from app.base.users import service as users
from app.base.users.models import User
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.milestones import service
from app.features.milestones.schemas import (
    MilestoneOut,
    ProjectMilestoneOut,
    VerificationOut,
    VerifyIn,
    VerifyOut,
)

router = APIRouter(tags=["milestones"])

SupervisorDep = Annotated[User, Depends(users.require_role("supervisor"))]
ClientDep = Annotated[User, Depends(users.require_role("client"))]


@router.post(
    "/milestones/{milestone_id}/claim",
    response_model=MilestoneOut,
    dependencies=[Depends(users.require_role("contractor"))],
)
async def claim_milestone(
    milestone_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    actor: CurrentActor,
    key: IdempotencyKeyDep,
) -> Any:
    """Contractor: the work for this milestone is done. The supervisor verifies it next.

    Send an `Idempotency-Key` header: a retry with the same key returns the first answer.
    """
    scope = f"POST /milestones/{milestone_id}/claim by {actor.id}"
    saved: JSONResponse | None = await replay_or_none(session, key, scope)
    if saved is not None:
        return saved
    milestone = await service.claim(session, milestone_id, actor, request=request)
    body = MilestoneOut.model_validate(milestone).model_dump(mode="json")
    await remember(session, key, scope, 200, body)
    await session.commit()
    return body


@router.post("/milestones/{milestone_id}/verify", response_model=VerifyOut)
async def verify_milestone(
    milestone_id: uuid.UUID,
    data: VerifyIn,
    request: Request,
    session: SessionDep,
    supervisor: SupervisorDep,
    key: IdempotencyKeyDep,
) -> Any:
    """Assigned supervisor: verify a claimed milestone with a checklist, or reject it with a reason.

    `verified` moves it to `verified` (the client approves next); `rejected` sends it back to
    `funded` so the contractor can rework and claim again. Every photo in the checklist must be
    accepted supervisor evidence for this milestone. Send an `Idempotency-Key` header: the
    offline sync queue retries with the same key and gets the first answer back.
    """
    scope = f"POST /milestones/{milestone_id}/verify by {supervisor.id}"
    saved: JSONResponse | None = await replay_or_none(session, key, scope)
    if saved is not None:
        return saved
    milestone, verification = await service.verify(session, milestone_id, supervisor, data, request=request)
    body = VerifyOut(
        milestone=MilestoneOut.model_validate(milestone),
        verification=VerificationOut.model_validate(verification),
    ).model_dump(mode="json")
    await remember(session, key, scope, 200, body)
    await session.commit()
    return body


@router.post("/milestones/{milestone_id}/approve", response_model=MilestoneOut)
async def approve_milestone(
    milestone_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    client: ClientDep,
    key: IdempotencyKeyDep,
) -> Any:
    """Client: approve a verified milestone. Escrow is asked to release its money to the contractor.

    The milestone shows `approved` until the escrow partner confirms, then `released`.
    Send an `Idempotency-Key` header: a retry with the same key returns the first answer.
    """
    scope = f"POST /milestones/{milestone_id}/approve by {client.id}"
    saved: JSONResponse | None = await replay_or_none(session, key, scope)
    if saved is not None:
        return saved
    milestone = await service.approve(session, milestone_id, client, request=request)
    body = MilestoneOut.model_validate(milestone).model_dump(mode="json")
    await remember(session, key, scope, 200, body)
    await session.commit()
    return body


@router.get("/projects/{project_id}/milestones", response_model=list[ProjectMilestoneOut])
async def list_project_milestones(
    project_id: uuid.UUID, session: SessionDep, user: users.CurrentUserDep
) -> list[ProjectMilestoneOut]:
    """The project's milestones in order, each with its newest verification.

    For the project's client, contractor and assigned supervisor, and for ops (others get 403).
    """
    milestones = await service.list_for_member(session, user, project_id)
    latest = await service.latest_verifications(session, [m.id for m in milestones])
    result = []
    for milestone in milestones:
        item = ProjectMilestoneOut.model_validate(milestone)
        verification = latest.get(milestone.id)
        if verification is not None:
            item.latest_verification = VerificationOut.model_validate(verification)
        result.append(item)
    return result
