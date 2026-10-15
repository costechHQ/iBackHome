"""HTTP endpoints for supervisor vetting, assignment and spot checks. Owner: James.

Routes are mounted under /api/v1 automatically. Each one checks the role, calls the service and commits;
the rules live in service.py, rotation.py and projects.set_supervisor(). Write endpoints accept an
optional Idempotency-Key header.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.base.users.models import User
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.projects import service as projects
from app.features.supervision import rotation, service
from app.features.supervision.models import SpotCheck, SupervisorProfile
from app.features.supervision.schemas import (
    AssignSupervisor,
    ProjectSupervisorOut,
    SpotCheckComplete,
    SpotCheckCreate,
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
    body: SupervisorApplication,
    request: Request,
    session: SessionDep,
    actor: SupervisorUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Apply for vetting (or re-apply after a rejection). The application goes to ops as pending."""
    scope = f"PUT /supervisors/me/profile {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    profile = await service.submit_application(session, actor.id, body, request=request)
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
    request: Request,
    session: SessionDep,
    actor: OpsUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Approve (every check passed) or reject (with a reason) a supervisor's application."""
    scope = f"POST /supervisors/{supervisor_id}/vetting {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    profile = await service.vet(session, supervisor_id, body, actor.id, request=request)
    out = SupervisorProfileOut.model_validate(profile).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.post("/projects/{project_id}/supervisor", response_model=ProjectSupervisorOut)
async def assign_supervisor(
    project_id: uuid.UUID,
    body: AssignSupervisor,
    request: Request,
    session: SessionDep,
    actor: OpsUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Ops: assign a vetted supervisor who isn't related to the project's contractor."""
    scope = f"POST /projects/{project_id}/supervisor {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    project = await projects.set_supervisor(
        session, project_id, body.supervisor_id, actor.id, request=request
    )
    out = ProjectSupervisorOut(project_id=project.id, supervisor_id=body.supervisor_id).model_dump(
        mode="json"
    )
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.post("/projects/{project_id}/spot-checks", response_model=SpotCheckOut, status_code=201)
async def schedule_spot_check(
    project_id: uuid.UUID,
    body: SpotCheckCreate,
    request: Request,
    session: SessionDep,
    actor: OpsUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Ops: schedule an unannounced visit. Never shown to the contractor."""
    scope = f"POST /projects/{project_id}/spot-checks {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    spot_check = await rotation.schedule_project_spot_check(
        session, project_id, body.supervisor_id, body.scheduled_for, actor.id, request=request
    )
    out = SpotCheckOut.model_validate(spot_check).model_dump(mode="json")
    await remember(session, key, scope, 201, out)
    await session.commit()
    return JSONResponse(status_code=201, content=out)


@router.get("/supervisors/me/spot-checks", response_model=list[SpotCheckOut])
async def my_spot_checks(session: SessionDep, actor: SupervisorUser) -> list[SpotCheck]:
    """The visits this supervisor still has to make, soonest first."""
    return await service.list_my_spot_checks(session, actor.id)


@router.post("/spot-checks/{spot_check_id}/complete", response_model=SpotCheckOut)
async def complete_spot_check(
    spot_check_id: uuid.UUID,
    body: SpotCheckComplete,
    request: Request,
    session: SessionDep,
    actor: SupervisorUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """The visiting supervisor records what they found (once)."""
    scope = f"POST /spot-checks/{spot_check_id}/complete {actor.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    spot_check = await service.complete_spot_check(
        session, spot_check_id, actor.id, body.findings, request=request
    )
    out = SpotCheckOut.model_validate(spot_check).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)
