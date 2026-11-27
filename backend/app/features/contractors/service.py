"""Contractor vetting and the directory (ADR 0007, phase 1). Owner: Christopher.

Every state change is checked here and audited. Approval creates the contractor's user through
users.invite_contractor (so a number that belongs to another role is 409 role_conflict and that role is never
changed) and the `contractor_profiles` row, in one transaction.
"""

import uuid
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.payments.after_commit import after_commit
from app.base.users import service as users
from app.core import pagination
from app.core.errors import AppError
from app.features.contractors import applications
from app.features.contractors.models import (
    ContractorApplication,
    ContractorApplicationStatus,
    ContractorProfile,
    ProfileStatus,
)
from app.features.contractors.schemas import ContractorDecisionIn


def _not_found() -> AppError:
    return AppError("application_not_found", "That application doesn't exist.", 404)


async def list_applications(
    session: AsyncSession, *, status: str, cursor: str | None, limit: int
) -> tuple[list[ContractorApplication], str | None]:
    """Applications with this status, oldest first (the queue ops work through)."""
    query = select(ContractorApplication).where(ContractorApplication.status == status)
    if cursor is not None:
        at, row_id = pagination.decode_cursor(cursor)
        query = query.where(
            tuple_(ContractorApplication.created_at, ContractorApplication.id) > tuple_(at, row_id)
        )
    rows = list(
        await session.scalars(
            query.order_by(ContractorApplication.created_at, ContractorApplication.id).limit(limit + 1)
        )
    )
    return pagination.page(rows, limit, lambda a: (a.created_at, a.id))


async def get_application(
    session: AsyncSession, application_id: uuid.UUID, *, lock: bool = False
) -> ContractorApplication:
    query = select(ContractorApplication).where(ContractorApplication.id == application_id)
    if lock:
        query = query.with_for_update()
    row = await session.scalar(query)
    if row is None:
        raise _not_found()
    return row


def _missing_checks(application: ContractorApplication, decision: ContractorDecisionIn) -> list[str]:
    """Approval needs both references, and the registration when a CAC or CORBON number was given."""
    missing = []
    if (application.cac_rc_number or application.corbon_number) and not decision.registration_verified:
        missing.append("registration")
    if not decision.reference_1_verified:
        missing.append("reference 1")
    if not decision.reference_2_verified:
        missing.append("reference 2")
    return missing


async def decide(
    session: AsyncSession,
    application_id: uuid.UUID,
    decision: ContractorDecisionIn,
    actor_id: uuid.UUID,
    *,
    request: Request | None = None,
) -> ContractorApplication:
    """Record ops' decision (the caller commits).

    - 404 application_not_found
    - 409 application_decided: it was already approved or rejected
    - 422 vetting_checks_incomplete: approving without the required checks ticked
    - 409 role_conflict / contractor_suspended: the number belongs to another role or a suspended account
    - 409 profile_exists: this person already has a contractor profile
    """
    application = await get_application(session, application_id, lock=True)
    if application.status != ContractorApplicationStatus.PENDING.value:
        raise AppError("application_decided", "This application has already been decided.", 409)

    profile: ContractorProfile | None = None
    now = datetime.now(UTC)
    if decision.decision == "approved":
        missing = _missing_checks(application, decision)
        if missing:
            raise AppError(
                "vetting_checks_incomplete",
                f"Every check must pass before approval. Not yet passed: {', '.join(missing)}.",
                422,
            )
        # Done before anything is changed, so a refusal (another role, a suspended account) changes nothing.
        user = await users.invite_contractor(session, application.phone)
        if await session.scalar(select(ContractorProfile.id).where(ContractorProfile.user_id == user.id)):
            raise AppError("profile_exists", "This contractor already has a profile.", 409)
        profile = ContractorProfile(
            user_id=user.id,
            application_id=application.id,
            business_name=application.business_name,
            contact_name=application.contact_name,
            summary=(decision.summary or "").strip(),
            states_served=list(application.states_served),
            specialties=list(application.specialties),
            years_in_business=application.years_in_business,
            projects_completed=application.projects_completed,
            vetting_status=ProfileStatus.APPROVED.value,
            vetted_by=actor_id,
            vetted_at=now,
            listed=True,
        )

    before = audit.snapshot(application)
    application.registration_verified = decision.registration_verified
    application.reference_1_verified = decision.reference_1_verified
    application.reference_2_verified = decision.reference_2_verified
    application.ops_notes = decision.notes
    application.status = ContractorApplicationStatus(decision.decision).value
    application.rejection_reason = (
        decision.reason.strip() if decision.decision == "rejected" and decision.reason else None
    )
    application.decided_by = actor_id
    application.decided_at = now
    await session.flush()
    await session.refresh(application)
    await audit.record(
        session,
        actor_id,
        f"contractor_application.{decision.decision}",
        "contractor_application",
        application.id,
        before,
        audit.snapshot(application),
        request,
    )
    if profile is not None:
        session.add(profile)
        await session.flush()
        await audit.record(
            session, actor_id, "contractor.approved", "contractor_profile", profile.id, None,
            audit.snapshot(profile), request,
        )  # fmt: skip
    after_commit(session, applications.enqueue_decision_email, application.id)
    return application


async def list_contractors(
    session: AsyncSession,
    *,
    state: str | None,
    specialty: str | None,
    listed: bool | None,
    cursor: str | None,
    limit: int,
) -> tuple[list[ContractorProfile], str | None]:
    """The directory of approved contractors, newest first."""
    query = select(ContractorProfile).where(ContractorProfile.vetting_status == ProfileStatus.APPROVED.value)
    if state:
        query = query.where(ContractorProfile.states_served.contains([state]))
    if specialty:
        query = query.where(ContractorProfile.specialties.contains([specialty]))
    if listed is not None:
        query = query.where(ContractorProfile.listed.is_(listed))
    if cursor is not None:
        at, row_id = pagination.decode_cursor(cursor)
        query = query.where(tuple_(ContractorProfile.created_at, ContractorProfile.id) < tuple_(at, row_id))
    rows = list(
        await session.scalars(
            query.order_by(ContractorProfile.created_at.desc(), ContractorProfile.id.desc()).limit(limit + 1)
        )
    )
    return pagination.page(rows, limit, lambda p: (p.created_at, p.id))
