"""Milestone business rules.

Other features call these functions; they never update the milestones table themselves.
Every function takes the database session first and does NOT commit: the caller commits,
so the milestone change, ledger entries and audit entry land together or not at all.

Used by:
- Christopher (BoQ approval): create_for_project()
- Gabriel (escrow):           mark_funded(), mark_released(), mark_disputed(), mark_resolved()
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.milestones.models import Milestone, MilestoneStatus
from app.features.milestones.schemas import MilestoneGroup
from app.features.milestones.transitions import ALLOWED_TRANSITIONS, ActorRole

S = MilestoneStatus

# Which timestamp to stamp when a milestone enters a state.
_STAMP = {
    S.FUNDED: "funded_at",
    S.CLAIMED: "claimed_at",
    S.VERIFIED: "verified_at",
    S.APPROVED: "approved_at",
    S.RELEASED: "released_at",
}

MAX_MILESTONES = 20


async def get_milestone(session: AsyncSession, milestone_id: uuid.UUID, *, lock: bool = False) -> Milestone:
    query = select(Milestone).where(Milestone.id == milestone_id)
    if lock:
        # Row lock: two requests can't both move the same milestone at once.
        query = query.with_for_update()
    milestone = await session.scalar(query)
    if milestone is None:
        raise AppError("milestone_not_found", "Milestone not found.", 404)
    return milestone


async def list_for_project(session: AsyncSession, project_id: uuid.UUID) -> list[Milestone]:
    result = await session.scalars(
        select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.sequence)
    )
    return list(result)


async def transition(
    session: AsyncSession,
    milestone_id: uuid.UUID,
    to_status: MilestoneStatus,
    actor_role: ActorRole,
    actor_id: uuid.UUID | None = None,
) -> Milestone:
    """Move a milestone to `to_status`, or raise.

    - 404 milestone_not_found
    - 409 invalid_transition: this move is not in the state machine (including "stay where you are")
    - 403 transition_not_allowed: the move exists but this role may not make it

    `actor_id` is kept for the audit entry (added once `audit.record()` exists on backend day 2).
    """
    milestone = await get_milestone(session, milestone_id, lock=True)
    current = milestone.status
    allowed_roles = ALLOWED_TRANSITIONS.get((current, to_status))

    if allowed_roles is None:
        raise AppError(
            "invalid_transition",
            f"A milestone cannot move from '{current.value}' to '{to_status.value}'.",
            409,
        )
    if actor_role not in allowed_roles:
        raise AppError(
            "transition_not_allowed",
            f"A {actor_role.value} cannot move a milestone from '{current.value}' to '{to_status.value}'.",
            403,
        )

    now = datetime.now(UTC)
    milestone.status = to_status
    if to_status in _STAMP:
        setattr(milestone, _STAMP[to_status], now)
    if to_status == S.FUNDED and current in (S.CLAIMED, S.DISPUTED):
        # Back to funded for rework: the earlier claim no longer stands.
        milestone.claimed_at = None
        milestone.verified_at = None
        milestone.approved_at = None

    await session.flush()
    return milestone


async def create_for_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    groups: Sequence[MilestoneGroup],
    currency: str,
) -> list[Milestone]:
    """Create the project's milestones in order (sequence 1, 2, 3...), all `pending`.

    Called once, when the BoQ is approved by client, contractor and ops.
    """
    if not groups:
        raise AppError("no_milestones", "At least one milestone is required.", 422)
    if len(groups) > MAX_MILESTONES:
        raise AppError("too_many_milestones", f"At most {MAX_MILESTONES} milestones per project.", 422)
    if len(currency) != 3 or not currency.isalpha() or not currency.isupper():
        raise AppError("invalid_currency", "Currency must be a 3-letter code such as NGN.", 422)

    existing = await session.scalar(
        select(func.count()).select_from(Milestone).where(Milestone.project_id == project_id)
    )
    if existing:
        raise AppError("milestones_already_exist", "This project already has milestones.", 409)

    milestones = [
        Milestone(
            project_id=project_id,
            sequence=index,
            name=group.name.strip(),
            amount_minor=group.amount_minor,
            currency=currency,
            status=S.PENDING,
        )
        for index, group in enumerate(groups, start=1)
    ]
    session.add_all(milestones)
    await session.flush()
    return milestones


# --- For Gabriel (escrow) ---------------------------------------------------------------


async def mark_funded(session: AsyncSession, milestone_id: uuid.UUID) -> Milestone:
    """Escrow confirmed the money for this milestone is held."""
    return await transition(session, milestone_id, S.FUNDED, ActorRole.SYSTEM)


async def mark_released(session: AsyncSession, milestone_id: uuid.UUID) -> Milestone:
    """Escrow confirmed the release of an approved milestone."""
    return await transition(session, milestone_id, S.RELEASED, ActorRole.SYSTEM)


async def mark_disputed(session: AsyncSession, milestone_id: uuid.UUID, client_id: uuid.UUID) -> Milestone:
    """The client disputed a verified milestone."""
    return await transition(session, milestone_id, S.DISPUTED, ActorRole.CLIENT, client_id)


async def mark_resolved(
    session: AsyncSession,
    milestone_id: uuid.UUID,
    outcome: Literal["release", "rework"],
    ops_user_id: uuid.UUID,
) -> Milestone:
    """Ops resolved a dispute.

    - "release": the contractor was right. Call this only after escrow confirms the money
      has been released, so `released` always means the money moved.
    - "rework":  back to `funded`; the contractor fixes the work and claims again.
    """
    if outcome == "release":
        return await transition(session, milestone_id, S.RELEASED, ActorRole.OPS, ops_user_id)
    if outcome == "rework":
        return await transition(session, milestone_id, S.FUNDED, ActorRole.OPS, ops_user_id)
    raise AppError("invalid_outcome", "Outcome must be 'release' or 'rework'.", 422)
