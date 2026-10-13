"""HTTP endpoints for supervisor vetting and spot checks. Owner: James.

Routes are mounted under /api/v1 automatically. Each one checks the role, calls service.py and commits;
the rules live in service.py. Write endpoints accept an optional Idempotency-Key header.

Waiting on Christopher's projects service (Day 3): POST /projects/{id}/supervisor and
POST /projects/{id}/spot-checks (they need the project's contractor and assigned supervisor).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.base.users.models import User
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.supervision import service
from app.features.supervision.models import SpotCheck, SupervisorProfile
from app.features.supervision.schemas import (
    SpotCheckComplete,
    SpotCheckOut,
    SupervisorApplication,
    SupervisorProfileOut,
    VettingDecision,
)

router = APIRouter(tags=["supervision"])

OpsUser = Annotated[User, Depends(users.require_role("ops"))]
SupervisorUser = Annotated[User, Depends(users.require_role("supervisor"))]


@router.put("/supervisors/me/profile", response_model=SupervisorProfileOut)
async def submit_application(
    body: SupervisorApplication, session: SessionDep, actor: SupervisorUser, key: IdempotencyKeyDep
) -> JSONResponse:
    """Apply for vetting (or re-apply after a rejection). The application goes to ops as pending."""
    scope = f"PUT /supervisors/me/profile {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    profile = await service.submit_application(session, actor.id, body)
    out = SupervisorProfileOut.model_validate(profile).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.get("/supervisors/me/profile", response_model=SupervisorProfileOut)
async def my_profile(session: SessionDep, actor: SupervisorUser) -> SupervisorProfile:
    return await service.get_profile(session, actor.id)


@router.post("/supervisors/{supervisor_id}/vetting", response_model=SupervisorProfileOut)
async def vet_supervisor(
    supervisor_id: uuid.UUID,
    body: VettingDecision,
    session: SessionDep,
    actor: OpsUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Approve (every check passed) or reject (with a reason) a supervisor's application."""
    scope = f"POST /supervisors/{supervisor_id}/vetting {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    profile = await service.vet(session, supervisor_id, body, actor.id)
    out = SupervisorProfileOut.model_validate(profile).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.get("/supervisors/me/spot-checks", response_model=list[SpotCheckOut])
async def my_spot_checks(session: SessionDep, actor: SupervisorUser) -> list[SpotCheck]:
    """The visits this supervisor still has to make, soonest first."""
    return await service.list_my_spot_checks(session, actor.id)


@router.post("/spot-checks/{spot_check_id}/complete", response_model=SpotCheckOut)
async def complete_spot_check(
    spot_check_id: uuid.UUID,
    body: SpotCheckComplete,
    session: SessionDep,
    actor: SupervisorUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """The visiting supervisor records what they found (once)."""
    scope = f"POST /spot-checks/{spot_check_id}/complete {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    spot_check = await service.complete_spot_check(session, spot_check_id, actor.id, body.findings)
    out = SpotCheckOut.model_validate(spot_check).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)
