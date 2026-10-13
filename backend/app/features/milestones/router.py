"""HTTP endpoints for milestones.

Day 2: POST /milestones/{id}/claim. Verify and approve endpoints and the project list come on day 3.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.base.audit.actor import CurrentActor
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.milestones import service
from app.features.milestones.schemas import MilestoneOut

router = APIRouter(tags=["milestones"])


@router.post("/milestones/{milestone_id}/claim", response_model=MilestoneOut)
async def claim_milestone(
    milestone_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    actor: CurrentActor,
    key: IdempotencyKeyDep = None,
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
