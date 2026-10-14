"""Business rules for projects and sites. Owner: Christopher.

Every function takes the database session first and does NOT commit: the caller commits, so a
change and its audit entry land together or not at all.

Who may see a project (spec: "Auth, roles and permissions"): its client, its contractor, its
assigned supervisor, and ops. `require_project_member()` is that check; every project route goes
through it, and other features use it for their project-scoped routes.

Used by:
- every feature with project routes:  require_project_member(), get_project()
- Abigail (evidence checks):          get_project_geofence(), get_geofence(session, site_id)
- James (supervisor assignment):      set_supervisor(), get_contractor_phone()
- Lilian (milestone claims):          get_project() (status, contractor_id)
- BoQ approval (Day 4), escrow:       transition()
"""

import json
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.geo import service as geo
from app.base.users import service as users
from app.base.users.models import Role, User, UserStatus
from app.core import pagination
from app.core.errors import AppError
from app.features.projects.models import SRID, Project, ProjectStatus, Site
from app.features.projects.schemas import Pin, ProjectCreate, SiteOut, SiteSet
from app.features.projects.transitions import ALLOWED_TRANSITIONS, ActorRole
from app.features.supervision import service as supervision

S = ProjectStatus


def _not_found() -> AppError:
    return AppError("project_not_found", "Project not found.", 404)


async def get_project(session: AsyncSession, project_id: uuid.UUID, *, lock: bool = False) -> Project:
    """The project, with no membership check (for other features' rules). 404 project_not_found."""
    query = select(Project).where(Project.id == project_id)
    if lock:
        # Row lock: two requests can't change the same project at once; re-read after the lock.
        query = query.with_for_update().execution_options(populate_existing=True)
    project = await session.scalar(query)
    if project is None:
        raise _not_found()
    return project


def is_member(user: User, project: Project) -> bool:
    return user.role == Role.OPS.value or user.id in (
        project.client_id,
        project.contractor_id,
        project.supervisor_id,
    )


async def require_project_member(
    session: AsyncSession, user: User, project_id: uuid.UUID, *, lock: bool = False
) -> Project:
    """The project, if `user` is its client, contractor or assigned supervisor, or is ops.

    - 404 project_not_found
    - 403 not_project_member
    """
    project = await get_project(session, project_id, lock=lock)
    if not is_member(user, project):
        raise AppError("not_project_member", "You are not on this project.", 403)
    return project


async def create_project(
    session: AsyncSession, client: User, data: ProjectCreate, *, request: Request | None = None
) -> Project:
    """A client creates a draft project, optionally inviting the contractor by phone.

    - 403 forbidden_role: not a client
    - 422 invalid_phone / phone_needs_country_code, 409 role_conflict / contractor_suspended (the invite)
    """
    if client.role != Role.CLIENT.value:
        raise AppError("forbidden_role", "Only a client can create a project.", 403)
    contractor_id = None
    if data.contractor_phone is not None:
        contractor_id = (await users.invite_contractor(session, data.contractor_phone)).id

    project = Project(
        client_id=client.id,
        contractor_id=contractor_id,
        title=data.title,
        address=data.address,
        currency=data.currency,
        budget_minor=data.budget_minor,
        status=S.DRAFT.value,
    )
    session.add(project)
    await session.flush()
    await session.refresh(project)
    await audit.record(
        session,
        client.id,
        "project.created",
        "project",
        project.id,
        after=audit.snapshot(project),
        request=request,
    )
    return project


async def list_projects(
    session: AsyncSession, user: User, *, cursor: str | None = None, limit: int = pagination.DEFAULT_LIMIT
) -> tuple[list[Project], str | None]:
    """Newest first: every project for ops, otherwise the ones the user is a party to."""
    if not 1 <= limit <= pagination.MAX_LIMIT:
        raise AppError("invalid_limit", f"limit must be between 1 and {pagination.MAX_LIMIT}.", 422)
    query = select(Project)
    if user.role != Role.OPS.value:
        query = query.where(
            or_(
                Project.client_id == user.id,
                Project.contractor_id == user.id,
                Project.supervisor_id == user.id,
            )
        )
    if cursor is not None:
        at, row_id = pagination.decode_cursor(cursor)
        query = query.where(tuple_(Project.created_at, Project.id) < tuple_(at, row_id))
    query = query.order_by(Project.created_at.desc(), Project.id.desc()).limit(limit + 1)
    rows = list(await session.scalars(query))
    return pagination.page(rows, limit, lambda p: (p.created_at, p.id))


# --- Sites ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _SiteRow:
    id: uuid.UUID
    location_ewkt: str
    geofence_ewkt: str
    out: SiteOut


async def _site_row(session: AsyncSession, project_id: uuid.UUID) -> _SiteRow | None:
    row = (
        await session.execute(
            select(
                Site.id,
                func.ST_Y(Site.location),
                func.ST_X(Site.location),
                func.ST_AsGeoJSON(Site.geofence),
                func.ST_AsEWKT(Site.location),
                func.ST_AsEWKT(Site.geofence),
                Site.updated_at,
            ).where(Site.project_id == project_id)
        )
    ).one_or_none()
    if row is None:
        return None
    site_id, lat, lon, geojson, location_ewkt, geofence_ewkt, updated_at = row
    out = SiteOut(location=Pin(lat=lat, lon=lon), geofence=json.loads(geojson), updated_at=updated_at)
    return _SiteRow(id=site_id, location_ewkt=location_ewkt, geofence_ewkt=geofence_ewkt, out=out)


async def get_site(session: AsyncSession, project_id: uuid.UUID) -> SiteOut | None:
    """The project's pin and geofence (GeoJSON), or None if not set yet. No membership check."""
    row = await _site_row(session, project_id)
    return row.out if row else None


async def set_site(
    session: AsyncSession, user: User, project_id: uuid.UUID, data: SiteSet, *, request: Request | None = None
) -> SiteOut:
    """Set or replace the project's pin and geofence (the project's client, or ops).

    - 404 project_not_found, 403 not_project_member / forbidden_role
    - 422 invalid_geofence (geo.parse_polygon rules), 422 pin_outside_geofence
    """
    if user.role not in (Role.CLIENT.value, Role.OPS.value):
        raise AppError("forbidden_role", "Only the project's client or ops can set the site.", 403)
    # Lock the project so two saves of a first site can't both insert one.
    await require_project_member(session, user, project_id, lock=True)

    fence = geo.parse_polygon(data.geofence)
    pin = data.location
    if not await geo.inside_geofence(session, fence.ewkt, pin.lat, pin.lon, buffer_m=0):
        raise AppError("pin_outside_geofence", "The site pin must be inside the geofence.", 422)
    location_ewkt = f"SRID={SRID};POINT({pin.lon} {pin.lat})"

    existing = await _site_row(session, project_id)
    before: dict[str, Any] | None = None
    if existing is None:
        site = Site(project_id=project_id, location=location_ewkt, geofence=fence.ewkt)
        session.add(site)
        await session.flush()
        site_id = site.id
    else:
        before = {"location": existing.location_ewkt, "geofence": existing.geofence_ewkt}
        site = await session.get_one(Site, existing.id)
        site.location = location_ewkt
        site.geofence = fence.ewkt
        await session.flush()
        site_id = existing.id

    saved = await _site_row(session, project_id)
    assert saved is not None  # noqa: S101 - just written in this transaction
    await audit.record(
        session,
        user.id,
        "site.set",
        "site",
        site_id,
        before=before,
        after={
            "project_id": str(project_id),
            "location": saved.location_ewkt,
            "geofence": saved.geofence_ewkt,
        },
        request=request,
    )
    return saved.out


async def get_geofence(session: AsyncSession, site_id: uuid.UUID) -> str:
    """The site's geofence as EWKT ("SRID=4326;POLYGON((lon lat, ...))") for geo.inside_geofence().

    - 404 site_not_found
    """
    ewkt = await session.scalar(select(func.ST_AsEWKT(Site.geofence)).where(Site.id == site_id))
    if ewkt is None:
        raise AppError("site_not_found", "Site not found.", 404)
    return str(ewkt)


async def get_project_geofence(session: AsyncSession, project_id: uuid.UUID) -> str:
    """Like get_geofence(), by project. 404 site_not_set if the project has no site yet."""
    ewkt = await session.scalar(select(func.ST_AsEWKT(Site.geofence)).where(Site.project_id == project_id))
    if ewkt is None:
        raise AppError("site_not_set", "This project's site has not been set yet.", 404)
    return str(ewkt)


# --- Supervisor assignment (James's POST /projects/{id}/supervisor calls this) --------------------


async def get_contractor_phone(session: AsyncSession, project_id: uuid.UUID) -> str | None:
    """The contractor's E.164 phone, or None if no contractor yet. 404 project_not_found."""
    project = await get_project(session, project_id)
    if project.contractor_id is None:
        return None
    contractor = await users.get_user(session, project.contractor_id)
    return contractor.phone if contractor else None


async def set_supervisor(
    session: AsyncSession,
    project_id: uuid.UUID,
    supervisor_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    request: Request | None = None,
) -> Project:
    """Assign the project's supervisor. The checks live here, so no caller can skip them.

    - 404 project_not_found, 404 user_not_found
    - 409 project_completed
    - 422 not_a_supervisor: the user's role is not supervisor
    - 409 supervisor_suspended
    - 409 supervisor_not_vetted / supervisor_related_to_contractor (supervision.ensure_assignable)
    Assigning the supervisor already on the project changes nothing and writes no audit entry.
    """
    project = await get_project(session, project_id, lock=True)
    if project.status == S.COMPLETED.value:
        raise AppError("project_completed", "A completed project can't get a new supervisor.", 409)
    supervisor = await users.get_user(session, supervisor_id)
    if supervisor is None:
        raise AppError("user_not_found", "User not found.", 404)
    if supervisor.role != Role.SUPERVISOR.value:
        raise AppError("not_a_supervisor", "Only a user with the supervisor role can be assigned.", 422)
    if supervisor.status != UserStatus.ACTIVE.value:
        raise AppError("supervisor_suspended", "This supervisor's account is suspended.", 409)
    if project.supervisor_id == supervisor_id:
        return project

    await supervision.ensure_assignable(
        session, supervisor_id, await get_contractor_phone(session, project_id)
    )

    before = audit.snapshot(project)
    project.supervisor_id = supervisor_id
    await session.flush()
    await session.refresh(project)
    await audit.record(
        session,
        actor_id,
        "project.supervisor_assigned",
        "project",
        project.id,
        before=before,
        after=audit.snapshot(project),
        request=request,
    )
    return project


# --- Status ---------------------------------------------------------------------------------------


async def transition(
    session: AsyncSession,
    project_id: uuid.UUID,
    to_status: ProjectStatus,
    actor_role: ActorRole,
    actor_id: uuid.UUID | None = None,
    *,
    request: Request | None = None,
) -> Project:
    """Move a project to `to_status` and write the audit entry ("project.<status>"), or raise.

    - 404 project_not_found
    - 409 invalid_transition: the move is not in transitions.py (including "stay where you are")
    - 403 transition_not_allowed: the move exists but this role may not make it
    `actor_id` is None for the system. Callers check their own conditions (e.g. all three BoQ approvals).
    """
    project = await get_project(session, project_id, lock=True)
    current = S(project.status)
    allowed_roles = ALLOWED_TRANSITIONS.get((current, to_status))
    if allowed_roles is None:
        raise AppError(
            "invalid_transition", f"A project cannot move from '{current.value}' to '{to_status.value}'.", 409
        )
    if actor_role not in allowed_roles:
        raise AppError(
            "transition_not_allowed",
            f"A {actor_role.value} cannot move a project from '{current.value}' to '{to_status.value}'.",
            403,
        )
    before = audit.snapshot(project)
    project.status = to_status.value
    await session.flush()
    await session.refresh(project)
    await audit.record(
        session,
        actor_id,
        f"project.{to_status.value}",
        "project",
        project.id,
        before=before,
        after={**audit.snapshot(project), "actor_role": actor_role.value},
        request=request,
    )
    return project
