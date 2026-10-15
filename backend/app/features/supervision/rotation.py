"""Supervision rules that need a project: project spot checks and supervisor rotation. Owner: James.

Kept apart from service.py because projects.service imports supervision.service (for
ensure_assignable), so service.py can't import projects back.

Rotation (spec, permissions): a supervisor "is rotated after two consecutive milestones on the same
project". next_supervisor() takes who verified each milestone, in order; Lilian's verifications
(her Day 3) will supply that list.
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
from app.features.supervision.models import SpotCheck

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
    verifiers: Sequence[uuid.UUID],
    *,
    choose: Callable[[list[uuid.UUID]], uuid.UUID] = _system_random.choice,
) -> uuid.UUID | None:
    """Who should take over the project now, or None if rotation isn't due (or nobody qualifies).

    Doesn't assign anyone: the caller passes the result to projects.set_supervisor(), which re-checks it.
    """
    project = await projects.get_project(session, project_id)
    if not rotation_due(project.supervisor_id, verifiers):
        return None
    return await pick_replacement(session, project_id, choose=choose)
