"""Supervision rules that need a project: project spot checks, supervisor rotation, and the ops list of
supervisors with their load and whether they may take a project. Owner: James.

Kept apart from service.py because projects.service imports supervision.service (for
ensure_assignable), so service.py can't import projects back.

Rotation (spec, permissions): a supervisor "is rotated after two consecutive milestones on the same
project". next_supervisor() reads who verified each milestone, in order, from Lilian's
`milestones.list_verifiers()`.
"""

import random
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.base.users.models import Role, UserStatus
from app.core.errors import AppError
from app.features.projects import service as projects
from app.features.supervision import service
from app.features.supervision.models import SpotCheck, VettingStatus
from app.features.supervision.schemas import SupervisorListItem

ROTATE_AFTER_MILESTONES = 2

# Rotation and spot checks exist to stop collusion, so the next supervisor must not be predictable.
_system_random = random.SystemRandom()


async def _active_supervisor(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Same refusals as projects.set_supervisor(), for people who visit without being assigned."""
    user = await users.get_user(session, user_id)
    if user is None:
        raise AppError("user_not_found", "User not found.", 404)
    if user.role != Role.SUPERVISOR.value:
        raise AppError("not_a_supervisor", "Only a user with the supervisor role can do this.", 422)
    if user.status != UserStatus.ACTIVE.value:
        raise AppError("supervisor_suspended", "This supervisor's account is suspended.", 409)


async def schedule_project_spot_check(
    session: AsyncSession,
    project_id: uuid.UUID,
    supervisor_id: uuid.UUID,
    scheduled_for: datetime,
    actor_id: uuid.UUID,
    *,
    request: Request | None = None,
) -> SpotCheck:
    """Ops schedules an unannounced visit to a project.

    - 404 project_not_found, 409 project_completed
    - 404 user_not_found, 422 not_a_supervisor, 409 supervisor_suspended
    - plus every refusal of service.schedule_spot_check()
    """
    project = await projects.get_project(session, project_id)
    if project.status == "completed":
        raise AppError("project_completed", "A completed project can't get a spot check.", 409)
    await _active_supervisor(session, supervisor_id)
    return await service.schedule_spot_check(
        session,
        project_id,
        supervisor_id,
        scheduled_for,
        actor_id,
        assigned_supervisor_id=project.supervisor_id,
        contractor_phone=await projects.get_contractor_phone(session, project_id),
        request=request,
    )


async def project_spot_checks(
    session: AsyncSession, project_id: uuid.UUID, viewer_role: str
) -> list[SpotCheck]:
    """A project's spot checks for ops, soonest first. 404 project_not_found, 403 spot_checks_hidden."""
    await projects.get_project(session, project_id)
    return await service.list_project_spot_checks(session, project_id, viewer_role)


async def list_for_ops(
    session: AsyncSession, status: VettingStatus, project_id: uuid.UUID | None = None
) -> list[SupervisorListItem]:
    """Supervisors with this vetting status, with their load (unfinished projects). With a project, also
    whether each is its current supervisor and whether they declared its contractor as a relative (then
    they can't be assigned or spot-check it). Read-only. 404 project_not_found."""
    current: uuid.UUID | None = None
    contractor_phone: str | None = None
    if project_id is not None:
        current = (await projects.get_project(session, project_id)).supervisor_id
        contractor_phone = await projects.get_contractor_phone(session, project_id)
    loads = await projects.supervisor_loads(session)
    items: list[SupervisorListItem] = []
    for profile in await service.list_profiles(session, status):
        user = await users.get_user(session, profile.user_id)
        if user is None:
            continue
        related: bool | None = None
        if project_id is not None:
            related = bool(contractor_phone) and await service.is_related(
                session, profile.user_id, contractor_phone or ""
            )
        items.append(
            SupervisorListItem(
                user_id=profile.user_id,
                full_name=user.full_name,
                phone=user.phone,
                account_status=user.status,
                registration_body=profile.registration_body,
                vetting_status=profile.vetting_status,
                vetted_at=profile.vetted_at,
                rating=profile.rating,
                active_projects=loads.get(profile.user_id, 0),
                related_contractors=len(await service.list_relations(session, profile.user_id)),
                assigned_here=None if project_id is None else profile.user_id == current,
                related_to_contractor=related,
            )
        )
    return items


def rotation_due(current_supervisor_id: uuid.UUID | None, verifiers: Sequence[uuid.UUID]) -> bool:
    """True when the current supervisor verified each of the last two milestones in a row.

    `verifiers` is who verified each verified milestone, in milestone order.
    """
    if current_supervisor_id is None or len(verifiers) < ROTATE_AFTER_MILESTONES:
        return False
    return all(v == current_supervisor_id for v in verifiers[-ROTATE_AFTER_MILESTONES:])


async def pick_replacement(
    session: AsyncSession,
    project_id: uuid.UUID,
    *,
    choose: Callable[[list[uuid.UUID]], uuid.UUID] = _system_random.choice,
) -> uuid.UUID | None:
    """A vetted, active supervisor other than the current one and not related to the contractor.

    None when nobody else qualifies (ops then keeps the current supervisor or vets more people).
    """
    project = await projects.get_project(session, project_id)
    contractor_phone = await projects.get_contractor_phone(session, project_id)
    eligible: list[uuid.UUID] = []
    for candidate in await service.list_vetted(session):
        if candidate == project.supervisor_id:
            continue
        user = await users.get_user(session, candidate)
        if user is None or user.role != Role.SUPERVISOR.value or user.status != UserStatus.ACTIVE.value:
            continue
        if contractor_phone and await service.is_related(session, candidate, contractor_phone):
            continue
        eligible.append(candidate)
    return choose(eligible) if eligible else None


async def next_supervisor(
    session: AsyncSession,
    project_id: uuid.UUID,
    *,
    choose: Callable[[list[uuid.UUID]], uuid.UUID] = _system_random.choice,
) -> uuid.UUID | None:
    """Who should take over the project now, or None if rotation isn't due (or nobody qualifies).

    Rotation is due when the current supervisor verified the last two verified milestones
    (`milestones.list_verifiers()`; a milestone sent back for rework drops out). Doesn't assign
    anyone: the caller passes the result to projects.set_supervisor(), which re-checks it.
    """
    # Imported here: milestones imports escrow, which imports more of the app than supervision needs.
    from app.features.milestones import service as milestones

    project = await projects.get_project(session, project_id)
    verifiers = await milestones.list_verifiers(session, project_id)
    if not rotation_due(project.supervisor_id, verifiers):
        return None
    return await pick_replacement(session, project_id, choose=choose)
