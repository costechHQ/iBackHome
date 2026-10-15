"""Milestone business rules.

Other features call these functions; they never update the milestones table themselves.
Every function takes the database session first and does NOT commit: the caller commits,
so the milestone change, ledger entries and audit entry land together or not at all.

Every successful transition writes an audit entry ("milestone.<new status>") in the same
transaction, with the milestone before and after.

Used by:
- Christopher (BoQ approval): create_for_project()
- Gabriel (escrow):           mark_funded(), mark_released(), mark_disputed(), mark_resolved()
- James (rotation):           list_verifiers()

Endpoints (router.py): claim (contractor), verify (assigned supervisor), approve (client),
and the project's milestone list (members and ops).
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.audit.actor import Actor
from app.base.users.models import User
from app.core.errors import AppError
from app.features.escrow import service as escrow
from app.features.milestones import evidence_check
from app.features.milestones.models import Milestone, MilestoneStatus, Verification
from app.features.milestones.schemas import MilestoneGroup, VerifyIn
from app.features.milestones.transitions import ALLOWED_TRANSITIONS, ActorRole
from app.features.projects import service as projects
from app.features.projects.models import Project

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
        # populate_existing re-reads the row after the lock, so we never act on a stale status.
        query = query.with_for_update().execution_options(populate_existing=True)
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
    *,
    request: Request | None = None,
) -> Milestone:
    """Move a milestone to `to_status` and write the audit entry, or raise.

    - 404 milestone_not_found
    - 409 invalid_transition: this move is not in the state machine (including "stay where you are")
    - 403 transition_not_allowed: the move exists but this role may not make it

    `actor_id` is None for the system (escrow webhooks). Pass `request` from an endpoint so the
    audit entry records the IP and device.
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

    before = audit.snapshot(milestone)
    now = datetime.now(UTC)
    milestone.status = to_status
    if to_status in _STAMP:
        setattr(milestone, _STAMP[to_status], now)
    if to_status == S.FUNDED and current in (S.CLAIMED, S.DISPUTED):
        # Back to funded for rework: the earlier claim no longer stands.
        milestone.claimed_at = None
        milestone.verified_at = None
        milestone.approved_at = None

    after = audit.snapshot(milestone)
    await session.flush()
    await audit.record(
        session,
        actor_id,
        f"milestone.{to_status.value}",
        "milestone",
        milestone.id,
        before=before,
        after={**after, "actor_role": actor_role.value},
        request=request,
    )
    return milestone


async def claim(
    session: AsyncSession, milestone_id: uuid.UUID, actor: Actor, *, request: Request | None = None
) -> Milestone:
    """The project's contractor says the work for this milestone is done.

    - 403 transition_not_allowed: the user is not a contractor
    - 404 milestone_not_found
    - 403 not_project_contractor: a contractor, but not this project's contractor
    - 409 project_not_active: the project is draft, in BoQ review, paused or completed
    - 409 invalid_transition: the milestone is not `funded` (e.g. not yet funded, or already claimed)
    """
    if actor.role != ActorRole.CONTRACTOR:
        raise AppError("transition_not_allowed", "Only the project's contractor can claim a milestone.", 403)
    milestone = await get_milestone(session, milestone_id, lock=True)
    project = await projects.get_project(session, milestone.project_id)
    if project.contractor_id != actor.id:
        raise AppError("not_project_contractor", "You are not the contractor on this project.", 403)
    _require_active(project, "claimed")
    return await transition(session, milestone_id, S.CLAIMED, ActorRole.CONTRACTOR, actor.id, request=request)


def _require_active(project: Project, action: str) -> None:
    if project.status != "active":
        raise AppError(
            "project_not_active",
            f"Milestones can only be {action} on an active project (this one is '{project.status}').",
            409,
        )


def _require_status(milestone: Milestone, status: MilestoneStatus, action: str) -> None:
    """Refuse early with the state machine's 409, before slower checks give a confusing error."""
    if milestone.status != status:
        raise AppError(
            "invalid_transition",
            f"Only a {status.value} milestone can be {action} (this one is '{milestone.status.value}').",
            409,
        )


async def verify(
    session: AsyncSession,
    milestone_id: uuid.UUID,
    supervisor: User,
    data: VerifyIn,
    *,
    request: Request | None = None,
) -> tuple[Milestone, Verification]:
    """The project's assigned supervisor verifies or rejects a claimed milestone.

    - `verified`: every photo the checklist points to must be this milestone's accepted
      supervisor evidence (`evidence.accepted_for_milestone()`); contractor uploads never count.
      The milestone moves `claimed` -> `verified`.
    - `rejected`: the milestone goes back to `funded` with the reason in `notes`;
      the contractor reworks and claims again.

    Errors:
    - 403 transition_not_allowed: the user is not a supervisor
    - 404 milestone_not_found / project_not_found
    - 403 not_assigned_supervisor: a supervisor, but not the one assigned to this project
    - 409 project_not_active
    - 409 invalid_transition: the milestone is not `claimed`
      (e.g. it was disputed while the supervisor was offline)
    - 409 evidence_not_accepted: a checklist photo is missing, still being checked, flagged,
      rejected, from another milestone, or was captured by the contractor
    """
    if supervisor.role != ActorRole.SUPERVISOR:
        raise AppError("transition_not_allowed", "Only the assigned supervisor can verify a milestone.", 403)
    milestone = await get_milestone(session, milestone_id, lock=True)
    project = await projects.get_project(session, milestone.project_id)
    if project.supervisor_id != supervisor.id:
        raise AppError("not_assigned_supervisor", "You are not the supervisor assigned to this project.", 403)
    _require_active(project, "verified")
    _require_status(milestone, S.CLAIMED, "verified or rejected")

    if data.decision == "verified":
        needed = data.evidence_ids()
        accepted = await evidence_check.accepted_evidence_ids(session, milestone.id)
        missing = needed - accepted
        if missing:
            raise AppError(
                "evidence_not_accepted",
                f"{len(missing)} of the checklist's {len(needed)} photos are not accepted supervisor "
                "evidence for this milestone yet. Wait for them to upload and pass the checks.",
                409,
            )

    verification = Verification(
        milestone_id=milestone.id,
        supervisor_id=supervisor.id,
        checklist=[item.model_dump(mode="json") for item in data.checklist],
        notes=data.notes,
        decision=data.decision,
        # The clock now, not the transaction start: two decisions in one transaction stay in order.
        created_at=datetime.now(UTC),
    )
    session.add(verification)
    await session.flush()
    await audit.record(
        session,
        supervisor.id,
        f"verification.{data.decision}",
        "verification",
        verification.id,
        after=audit.snapshot(verification),
        request=request,
    )
    to_status = S.VERIFIED if data.decision == "verified" else S.FUNDED
    milestone = await transition(
        session, milestone.id, to_status, ActorRole.SUPERVISOR, supervisor.id, request=request
    )
    return milestone, verification


async def approve(
    session: AsyncSession, milestone_id: uuid.UUID, client: User, *, request: Request | None = None
) -> Milestone:
    """The project's client approves a verified milestone and asks escrow to release its money.

    In one transaction: `verified` -> `approved`, then `escrow.request_release()`. If escrow
    refuses, nothing is saved. The milestone becomes `released` later, when the escrow partner
    confirms (Gabriel's webhook calls `mark_released()`).

    Errors:
    - 403 transition_not_allowed: the user is not a client
    - 404 milestone_not_found / project_not_found
    - 403 not_project_client: a client, but not this project's
    - 409 project_not_active
    - 409 invalid_transition: the milestone is not `verified`
    """
    if client.role != ActorRole.CLIENT:
        raise AppError("transition_not_allowed", "Only the project's client can approve a milestone.", 403)
    milestone = await get_milestone(session, milestone_id, lock=True)
    project = await projects.get_project(session, milestone.project_id)
    if project.client_id != client.id:
        raise AppError("not_project_client", "You are not the client on this project.", 403)
    _require_active(project, "approved")
    _require_status(milestone, S.VERIFIED, "approved")

    milestone = await transition(
        session, milestone.id, S.APPROVED, ActorRole.CLIENT, client.id, request=request
    )
    await escrow.request_release(session, milestone.id, client)
    return milestone


async def list_for_member(session: AsyncSession, user: User, project_id: uuid.UUID) -> list[Milestone]:
    """The project's milestones in order, for its client, contractor, assigned supervisor or ops.

    - 404 project_not_found
    - 403 not_project_member
    """
    await projects.require_project_member(session, user, project_id)
    return await list_for_project(session, project_id)


async def latest_verifications(
    session: AsyncSession, milestone_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, Verification]:
    """The newest verification of each milestone (so the contractor sees why a claim was rejected)."""
    if not milestone_ids:
        return {}
    rows = await session.scalars(
        select(Verification)
        .where(Verification.milestone_id.in_(milestone_ids))
        .order_by(Verification.milestone_id, Verification.created_at.desc(), Verification.id.desc())
        .distinct(Verification.milestone_id)
    )
    return {v.milestone_id: v for v in rows}


# Milestones that have been verified at some point and not sent back for rework since.
_VERIFIED_OR_LATER = (S.VERIFIED, S.APPROVED, S.DISPUTED, S.RELEASED)


async def list_verifiers(session: AsyncSession, project_id: uuid.UUID) -> list[uuid.UUID]:
    """Who verified each verified milestone of the project, in milestone order (for James's rotation).

    A milestone counts once it is verified, approved, disputed or released; its verifier is the
    supervisor of its newest `verified` decision. Milestones not verified yet are left out.
    """
    milestones = [m for m in await list_for_project(session, project_id) if m.status in _VERIFIED_OR_LATER]
    if not milestones:
        return []
    rows = await session.scalars(
        select(Verification)
        .where(
            Verification.milestone_id.in_([m.id for m in milestones]),
            Verification.decision == "verified",
        )
        .order_by(Verification.milestone_id, Verification.created_at.desc(), Verification.id.desc())
        .distinct(Verification.milestone_id)
    )
    by_milestone = {v.milestone_id: v.supervisor_id for v in rows}
    return [by_milestone[m.id] for m in milestones if m.id in by_milestone]


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
