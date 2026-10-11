"""Supervisor vetting, assignment and spot-check rules. Owner: James.

Every function takes the database session first and does NOT commit: the caller commits,
so a vetting decision and its audit entry land together or not at all.

Used by:
- James (assignment):   is_vetted(), ensure_assignable()
- Abigail (ops queue):  list_pending_vetting()
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.supervision.models import SpotCheck, SupervisorProfile, SupervisorRelation, VettingStatus
from app.features.supervision.schemas import SupervisorApplication, VettingDecision

CHECKS = ("registration_verified", "nin_verified", "guarantor_1_verified", "guarantor_2_verified")


async def get_profile(session: AsyncSession, user_id: uuid.UUID, *, lock: bool = False) -> SupervisorProfile:
    query = select(SupervisorProfile).where(SupervisorProfile.user_id == user_id)
    if lock:
        query = query.with_for_update()
    profile = await session.scalar(query)
    if profile is None:
        raise AppError("supervisor_profile_not_found", "This supervisor has not applied for vetting.", 404)
    return profile


async def submit_application(
    session: AsyncSession, user_id: uuid.UUID, application: SupervisorApplication
) -> SupervisorProfile:
    """Create or update a supervisor's application. Any change sends it back to ops as pending."""
    profile = await session.scalar(
        select(SupervisorProfile).where(SupervisorProfile.user_id == user_id).with_for_update()
    )
    if profile is not None and profile.vetting_status == VettingStatus.APPROVED:
        raise AppError("supervisor_already_vetted", "An approved profile can only be changed by ops.", 409)
    if profile is None:
        profile = SupervisorProfile(user_id=user_id)
        session.add(profile)

    profile.registration_body = application.registration_body
    profile.registration_no = application.registration_no
    profile.guarantor_1 = application.guarantor_1
    profile.guarantor_2 = application.guarantor_2
    for check in CHECKS:
        setattr(profile, check, False)
    profile.vetting_status = VettingStatus.PENDING
    profile.vetted_by = profile.vetted_at = profile.rejection_reason = None

    await session.execute(delete(SupervisorRelation).where(SupervisorRelation.supervisor_id == user_id))
    session.add_all(
        SupervisorRelation(
            supervisor_id=user_id, contractor_phone=r.contractor_phone, relationship=r.relationship
        )
        for r in {r.contractor_phone: r for r in application.related_contractors}.values()
    )
    await session.flush()
    return profile


async def vet(
    session: AsyncSession, supervisor_id: uuid.UUID, decision: VettingDecision, actor_id: uuid.UUID
) -> SupervisorProfile:
    """Record ops' decision.

    - 404 supervisor_profile_not_found
    - 422 vetting_checks_incomplete: approving without every check ticked (PRD FR-02)
    """
    profile = await get_profile(session, supervisor_id, lock=True)

    if decision.decision == "approved":
        missing = [c.removesuffix("_verified") for c in CHECKS if not getattr(decision, c)]
        if missing:
            raise AppError(
                "vetting_checks_incomplete",
                f"Every check must pass before approval. Not yet passed: {', '.join(missing)}.",
                422,
            )

    for check in CHECKS:
        setattr(profile, check, getattr(decision, check))
    profile.vetting_status = VettingStatus(decision.decision)
    profile.rejection_reason = decision.reason if decision.decision == "rejected" else None
    profile.vetted_by = actor_id
    profile.vetted_at = datetime.now(UTC)
    await session.flush()
    return profile


async def is_vetted(session: AsyncSession, user_id: uuid.UUID) -> bool:
    approved = await session.scalar(
        select(
            exists().where(
                SupervisorProfile.user_id == user_id,
                SupervisorProfile.vetting_status == VettingStatus.APPROVED,
            )
        )
    )
    return bool(approved)


async def list_pending_vetting(session: AsyncSession) -> list[SupervisorProfile]:
    """Applications waiting for ops, oldest first (for the ops queue)."""
    result = await session.scalars(
        select(SupervisorProfile)
        .where(SupervisorProfile.vetting_status == VettingStatus.PENDING)
        .order_by(SupervisorProfile.created_at)
    )
    return list(result)


async def is_related(session: AsyncSession, supervisor_id: uuid.UUID, contractor_phone: str) -> bool:
    related = await session.scalar(
        select(
            exists().where(
                SupervisorRelation.supervisor_id == supervisor_id,
                SupervisorRelation.contractor_phone == contractor_phone,
            )
        )
    )
    return bool(related)


async def ensure_assignable(
    session: AsyncSession, supervisor_id: uuid.UUID, contractor_phone: str | None
) -> None:
    """Raise unless this supervisor may be put on a project with this contractor.

    - 409 supervisor_not_vetted: no approved vetting
    - 409 supervisor_related_to_contractor: declared as related at vetting (spec: permissions)
    """
    if not await is_vetted(session, supervisor_id):
        raise AppError("supervisor_not_vetted", "Only a vetted supervisor can be assigned.", 409)
    if contractor_phone and await is_related(session, supervisor_id, contractor_phone):
        raise AppError(
            "supervisor_related_to_contractor",
            "This supervisor declared a relationship with the project's contractor.",
            409,
        )


# Spot checks: unannounced visits (PRD FR-11). Only ops schedules them and sees a project's list;
# the visiting supervisor sees their own. The contractor never sees them, or they wouldn't be unannounced.


async def schedule_spot_check(
    session: AsyncSession,
    project_id: uuid.UUID,
    supervisor_id: uuid.UUID,
    scheduled_for: datetime,
    scheduled_by: uuid.UUID,
    *,
    assigned_supervisor_id: uuid.UUID | None = None,
    contractor_phone: str | None = None,
) -> SpotCheck:
    """Schedule a visit by a vetted supervisor other than the project's own.

    - 422 spot_check_in_past: `scheduled_for` is not in the future
    - 409 spot_check_by_assigned_supervisor: a spot check also checks the project's supervisor
    - 409 supervisor_not_vetted / supervisor_related_to_contractor (same rules as assignment)
    """
    if scheduled_for <= datetime.now(UTC):
        raise AppError("spot_check_in_past", "A spot check must be scheduled in the future.", 422)
    if supervisor_id == assigned_supervisor_id:
        raise AppError(
            "spot_check_by_assigned_supervisor",
            "Choose a different supervisor from the one assigned to this project.",
            409,
        )
    await ensure_assignable(session, supervisor_id, contractor_phone)

    spot_check = SpotCheck(
        project_id=project_id,
        supervisor_id=supervisor_id,
        scheduled_by=scheduled_by,
        scheduled_for=scheduled_for.astimezone(UTC),
    )
    session.add(spot_check)
    await session.flush()
    return spot_check


async def list_project_spot_checks(
    session: AsyncSession, project_id: uuid.UUID, viewer_role: str
) -> list[SpotCheck]:
    """Every spot check on a project, soonest first. Ops only (403 spot_checks_hidden otherwise)."""
    if viewer_role != "ops":
        raise AppError("spot_checks_hidden", "Only ops can see a project's spot checks.", 403)
    result = await session.scalars(
        select(SpotCheck).where(SpotCheck.project_id == project_id).order_by(SpotCheck.scheduled_for)
    )
    return list(result)


async def list_my_spot_checks(session: AsyncSession, supervisor_id: uuid.UUID) -> list[SpotCheck]:
    """The visits a supervisor still has to make, soonest first."""
    result = await session.scalars(
        select(SpotCheck)
        .where(SpotCheck.supervisor_id == supervisor_id, SpotCheck.completed_at.is_(None))
        .order_by(SpotCheck.scheduled_for)
    )
    return list(result)


async def complete_spot_check(
    session: AsyncSession, spot_check_id: uuid.UUID, supervisor_id: uuid.UUID, findings: str
) -> SpotCheck:
    """The visiting supervisor records what they found.

    - 404 spot_check_not_found (also when it belongs to another supervisor, so ids don't leak)
    - 409 spot_check_already_completed
    """
    spot_check = await session.scalar(
        select(SpotCheck).where(SpotCheck.id == spot_check_id).with_for_update()
    )
    if spot_check is None or spot_check.supervisor_id != supervisor_id:
        raise AppError("spot_check_not_found", "Spot check not found.", 404)
    if spot_check.completed_at is not None:
        raise AppError("spot_check_already_completed", "This spot check has already been completed.", 409)
    spot_check.findings = findings
    spot_check.completed_at = datetime.now(UTC)
    await session.flush()
    return spot_check
