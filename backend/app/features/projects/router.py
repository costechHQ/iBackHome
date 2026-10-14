"""HTTP endpoints for projects and sites. Owner: Christopher.

Routes parse the request, check the role, and call service.py, which checks project membership.
POST /projects/{id}/supervisor is James's route (supervision); it calls service.set_supervisor().
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.base.users.models import User
from app.core import pagination
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.projects import service
from app.features.projects.schemas import (
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProjectPage,
    SiteOut,
    SiteSet,
)

router = APIRouter(tags=["projects"])

ClientUser = Annotated[User, Depends(users.require_role("client"))]
ClientOrOps = Annotated[User, Depends(users.require_role("client", "ops"))]


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(
    data: ProjectCreate, request: Request, session: SessionDep, user: ClientUser, key: IdempotencyKeyDep
) -> Any:
    """Client: create a draft project, optionally inviting the contractor by phone number.

    Send an `Idempotency-Key` header: a retry with the same key returns the first answer.
    """
    scope = f"POST /projects by {user.id}"
    saved: JSONResponse | None = await replay_or_none(session, key, scope)
    if saved is not None:
        return saved
    project = await service.create_project(session, user, data, request=request)
    body = ProjectOut.model_validate(project).model_dump(mode="json")
    await remember(session, key, scope, 201, body)
    await session.commit()
    return body


@router.get("/projects", response_model=ProjectPage)
async def list_projects(
    session: SessionDep,
    user: users.CurrentUserDep,
    cursor: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=pagination.DEFAULT_LIMIT, ge=1, le=pagination.MAX_LIMIT),
) -> ProjectPage:
    """The projects you are on (all projects for ops), newest first."""
    projects, next_cursor = await service.list_projects(session, user, cursor=cursor, limit=limit)
    return ProjectPage(items=[ProjectOut.model_validate(p) for p in projects], next_cursor=next_cursor)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: uuid.UUID, session: SessionDep, user: users.CurrentUserDep
) -> ProjectDetail:
    """One project with its site. Its client, contractor and supervisor, and ops."""
    project = await service.require_project_member(session, user, project_id)
    site = await service.get_site(session, project_id)
    return ProjectDetail(**ProjectOut.model_validate(project).model_dump(), site=site)


@router.put("/projects/{project_id}/site", response_model=SiteOut)
async def set_site(
    project_id: uuid.UUID,
    data: SiteSet,
    request: Request,
    session: SessionDep,
    user: ClientOrOps,
    key: IdempotencyKeyDep,
) -> Any:
    """The project's client, or ops: set or replace the pin and geofence (GeoJSON Polygon, [lon, lat]).

    The pin must be inside the geofence. Send an `Idempotency-Key` header to make retries safe.
    """
    scope = f"PUT /projects/{project_id}/site by {user.id}"
    saved: JSONResponse | None = await replay_or_none(session, key, scope)
    if saved is not None:
        return saved
    site = await service.set_site(session, user, project_id, data, request=request)
    body = site.model_dump(mode="json")
    await remember(session, key, scope, 200, body)
    await session.commit()
    return body
