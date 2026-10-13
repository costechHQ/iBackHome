"""Vetting and assignment rules (service.py). Needs Postgres (backend/conftest.py)."""

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.core.errors import AppError
from app.features.supervision import service
from app.features.supervision.models import VettingStatus
from app.features.supervision.schemas import DeclaredRelation, VettingDecision
from app.features.supervision.tests.factories import ALL_CHECKS, application, approval, make_user

CONTRACTOR_PHONE = "+2348012345678"


def rejection(reason: str) -> VettingDecision:
    return VettingDecision(decision="rejected", reason=reason)


async def test_new_application_is_pending_and_not_vetted(db_session: AsyncSession, applicant: User) -> None:
    profile = await service.get_profile(db_session, applicant.id)

    assert profile.vetting_status == VettingStatus.PENDING
    assert not await service.is_vetted(db_session, applicant.id)
    assert profile in await service.list_pending_vetting(db_session)


async def test_approval_with_every_check_vets_the_supervisor(
    db_session: AsyncSession, applicant: User, ops: User
) -> None:
    profile = await service.vet(db_session, applicant.id, approval(), ops.id)

    assert profile.vetting_status == VettingStatus.APPROVED
    assert (profile.vetted_by, profile.rejection_reason) == (ops.id, None)
    assert profile.vetted_at is not None
    assert await service.is_vetted(db_session, applicant.id)
    assert profile not in await service.list_pending_vetting(db_session)


@pytest.mark.parametrize("unticked", sorted(ALL_CHECKS))
async def test_approval_is_refused_while_any_check_is_unticked(
    db_session: AsyncSession, applicant: User, ops: User, unticked: str
) -> None:
    decision = VettingDecision.model_validate({"decision": "approved", **ALL_CHECKS, unticked: False})

    with pytest.raises(AppError) as error:
        await service.vet(db_session, applicant.id, decision, ops.id)

    assert (error.value.code, error.value.status_code) == ("vetting_checks_incomplete", 422)
    assert unticked.removesuffix("_verified") in error.value.message
    assert not await service.is_vetted(db_session, applicant.id)


async def test_rejection_keeps_the_reason(db_session: AsyncSession, applicant: User, ops: User) -> None:
    profile = await service.vet(db_session, applicant.id, rejection("Guarantor unreachable"), ops.id)

    assert profile.vetting_status == VettingStatus.REJECTED
    assert profile.rejection_reason == "Guarantor unreachable"
    assert not await service.is_vetted(db_session, applicant.id)


def test_rejection_needs_a_reason() -> None:
    with pytest.raises(ValidationError):
        VettingDecision(decision="rejected", reason="  ")


async def test_ops_can_revoke_an_approval(db_session: AsyncSession, vetted: User, ops: User) -> None:
    await service.vet(db_session, vetted.id, rejection("Fraud report"), ops.id)

    assert not await service.is_vetted(db_session, vetted.id)


async def test_vetting_someone_who_never_applied_is_404(db_session: AsyncSession, ops: User) -> None:
    with pytest.raises(AppError) as error:
        await service.vet(db_session, uuid.uuid4(), approval(), ops.id)

    assert (error.value.code, error.value.status_code) == ("supervisor_profile_not_found", 404)


async def test_reapplying_after_rejection_goes_back_to_pending(
    db_session: AsyncSession, applicant: User, ops: User
) -> None:
    await service.vet(db_session, applicant.id, rejection("NIN mismatch"), ops.id)

    profile = await service.submit_application(db_session, applicant.id, application())

    assert profile.vetting_status == VettingStatus.PENDING
    assert (profile.rejection_reason, profile.vetted_by, profile.nin_verified) == (None, None, False)


async def test_approved_supervisor_cannot_rewrite_their_application(
    db_session: AsyncSession, vetted: User
) -> None:
    with pytest.raises(AppError) as error:
        await service.submit_application(db_session, vetted.id, application())

    assert error.value.code == "supervisor_already_vetted"
    assert await service.is_vetted(db_session, vetted.id)


async def test_unvetted_supervisor_cannot_be_assigned(db_session: AsyncSession, applicant: User) -> None:
    with pytest.raises(AppError) as error:
        await service.ensure_assignable(db_session, applicant.id, CONTRACTOR_PHONE)

    assert (error.value.code, error.value.status_code) == ("supervisor_not_vetted", 409)


async def test_unknown_user_cannot_be_assigned(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await service.ensure_assignable(db_session, uuid.uuid4(), CONTRACTOR_PHONE)

    assert error.value.code == "supervisor_not_vetted"


async def test_vetted_supervisor_can_be_assigned(db_session: AsyncSession, vetted: User) -> None:
    await service.ensure_assignable(db_session, vetted.id, CONTRACTOR_PHONE)


async def test_supervisor_related_to_the_contractor_cannot_be_assigned(
    db_session: AsyncSession, ops: User
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    cousin = DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="cousin")
    await service.submit_application(db_session, supervisor.id, application(cousin))
    await service.vet(db_session, supervisor.id, approval(), ops.id)

    with pytest.raises(AppError) as error:
        await service.ensure_assignable(db_session, supervisor.id, CONTRACTOR_PHONE)

    assert (error.value.code, error.value.status_code) == ("supervisor_related_to_contractor", 409)
    await service.ensure_assignable(db_session, supervisor.id, "+2348099999999")  # anyone else is fine


async def test_relative_given_in_local_form_matches_the_contractors_account(
    db_session: AsyncSession, applicant: User
) -> None:
    local = DeclaredRelation(contractor_phone="0801 234 5678", relationship="brother")

    await service.submit_application(db_session, applicant.id, application(local))

    assert await service.is_related(db_session, applicant.id, CONTRACTOR_PHONE)


async def test_reapplying_replaces_declared_relations(db_session: AsyncSession, applicant: User) -> None:
    cousin = DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="cousin")
    same_cousin = DeclaredRelation(contractor_phone="08012345678", relationship="cousin")
    await service.submit_application(db_session, applicant.id, application(cousin, same_cousin))

    assert await service.is_related(db_session, applicant.id, CONTRACTOR_PHONE)
    await service.submit_application(db_session, applicant.id, application())
    assert not await service.is_related(db_session, applicant.id, CONTRACTOR_PHONE)


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("1234567", "invalid_phone"),
        ("447400123456", "phone_needs_country_code"),  # a UK number typed without its +
        ("someone@example.com", "invalid_phone"),
    ],
)
async def test_invalid_relative_phone_is_refused(
    db_session: AsyncSession, applicant: User, raw: str, code: str
) -> None:
    with pytest.raises(AppError) as error:
        await service.submit_application(
            db_session, applicant.id, application(DeclaredRelation(contractor_phone=raw, relationship="aunt"))
        )

    assert (error.value.code, error.value.status_code) == (code, 422)
