"""Vetting and assignment rules (service.py). Needs Postgres; see conftest.py."""

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.supervision import service
from app.features.supervision.models import VettingStatus
from app.features.supervision.schemas import DeclaredRelation, SupervisorApplication, VettingDecision

CONTRACTOR_PHONE = "+2348012345678"
OPS_ID = uuid.uuid4()
ALL_CHECKS = {
    "registration_verified": True,
    "nin_verified": True,
    "guarantor_1_verified": True,
    "guarantor_2_verified": True,
}


def application(*relations: DeclaredRelation) -> SupervisorApplication:
    return SupervisorApplication(
        registration_body="COREN",
        registration_no="R.12345",
        guarantor_1="Ngozi Eze, +2348031234567",
        guarantor_2="Emeka Obi, +2348039876543",
        related_contractors=list(relations),
    )


def approve() -> VettingDecision:
    return VettingDecision.model_validate({"decision": "approved", **ALL_CHECKS})


async def applied(session: AsyncSession, *relations: DeclaredRelation) -> uuid.UUID:
    supervisor_id = uuid.uuid4()
    await service.submit_application(session, supervisor_id, application(*relations))
    return supervisor_id


async def test_new_application_is_pending_and_not_vetted(db_session: AsyncSession) -> None:
    supervisor_id = await applied(db_session)

    profile = await service.get_profile(db_session, supervisor_id)
    assert profile.vetting_status == VettingStatus.PENDING
    assert not await service.is_vetted(db_session, supervisor_id)
    assert profile in await service.list_pending_vetting(db_session)


async def test_approval_with_every_check_vets_the_supervisor(db_session: AsyncSession) -> None:
    supervisor_id = await applied(db_session)

    profile = await service.vet(db_session, supervisor_id, approve(), OPS_ID)

    assert profile.vetting_status == VettingStatus.APPROVED
    assert (profile.vetted_by, profile.rejection_reason) == (OPS_ID, None)
    assert profile.vetted_at is not None
    assert await service.is_vetted(db_session, supervisor_id)
    assert profile not in await service.list_pending_vetting(db_session)


@pytest.mark.parametrize("unticked", sorted(ALL_CHECKS))
async def test_approval_is_refused_while_any_check_is_unticked(
    db_session: AsyncSession, unticked: str
) -> None:
    supervisor_id = await applied(db_session)

    with pytest.raises(AppError) as error:
        await service.vet(
            db_session,
            supervisor_id,
            VettingDecision.model_validate({"decision": "approved", **ALL_CHECKS, unticked: False}),
            OPS_ID,
        )

    assert (error.value.code, error.value.status_code) == ("vetting_checks_incomplete", 422)
    assert unticked.removesuffix("_verified") in error.value.message
    assert not await service.is_vetted(db_session, supervisor_id)


async def test_rejection_keeps_the_reason(db_session: AsyncSession) -> None:
    supervisor_id = await applied(db_session)

    profile = await service.vet(
        db_session,
        supervisor_id,
        VettingDecision(decision="rejected", reason="Guarantor unreachable"),
        OPS_ID,
    )

    assert profile.vetting_status == VettingStatus.REJECTED
    assert profile.rejection_reason == "Guarantor unreachable"
    assert not await service.is_vetted(db_session, supervisor_id)


def test_rejection_needs_a_reason() -> None:
    with pytest.raises(ValidationError):
        VettingDecision(decision="rejected", reason="  ")


async def test_ops_can_revoke_an_approval(db_session: AsyncSession) -> None:
    supervisor_id = await applied(db_session)
    await service.vet(db_session, supervisor_id, approve(), OPS_ID)

    await service.vet(
        db_session, supervisor_id, VettingDecision(decision="rejected", reason="Fraud report"), OPS_ID
    )

    assert not await service.is_vetted(db_session, supervisor_id)


async def test_vetting_someone_who_never_applied_is_404(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await service.vet(db_session, uuid.uuid4(), approve(), OPS_ID)

    assert (error.value.code, error.value.status_code) == ("supervisor_profile_not_found", 404)


async def test_reapplying_after_rejection_goes_back_to_pending(db_session: AsyncSession) -> None:
    supervisor_id = await applied(db_session)
    await service.vet(
        db_session, supervisor_id, VettingDecision(decision="rejected", reason="NIN mismatch"), OPS_ID
    )

    profile = await service.submit_application(db_session, supervisor_id, application())

    assert profile.vetting_status == VettingStatus.PENDING
    assert (profile.rejection_reason, profile.vetted_by, profile.nin_verified) == (None, None, False)


async def test_approved_supervisor_cannot_rewrite_their_application(db_session: AsyncSession) -> None:
    supervisor_id = await applied(db_session)
    await service.vet(db_session, supervisor_id, approve(), OPS_ID)

    with pytest.raises(AppError) as error:
        await service.submit_application(db_session, supervisor_id, application())

    assert error.value.code == "supervisor_already_vetted"
    assert await service.is_vetted(db_session, supervisor_id)


async def test_unvetted_supervisor_cannot_be_assigned(db_session: AsyncSession) -> None:
    supervisor_id = await applied(db_session)

    with pytest.raises(AppError) as error:
        await service.ensure_assignable(db_session, supervisor_id, CONTRACTOR_PHONE)

    assert (error.value.code, error.value.status_code) == ("supervisor_not_vetted", 409)


async def test_unknown_user_cannot_be_assigned(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await service.ensure_assignable(db_session, uuid.uuid4(), CONTRACTOR_PHONE)

    assert error.value.code == "supervisor_not_vetted"


async def test_vetted_supervisor_can_be_assigned(db_session: AsyncSession) -> None:
    supervisor_id = await applied(db_session)
    await service.vet(db_session, supervisor_id, approve(), OPS_ID)

    await service.ensure_assignable(db_session, supervisor_id, CONTRACTOR_PHONE)


async def test_supervisor_related_to_the_contractor_cannot_be_assigned(db_session: AsyncSession) -> None:
    supervisor_id = await applied(
        db_session, DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="cousin")
    )
    await service.vet(db_session, supervisor_id, approve(), OPS_ID)

    with pytest.raises(AppError) as error:
        await service.ensure_assignable(db_session, supervisor_id, CONTRACTOR_PHONE)

    assert (error.value.code, error.value.status_code) == ("supervisor_related_to_contractor", 409)
    await service.ensure_assignable(db_session, supervisor_id, "+2348099999999")  # anyone else is fine


async def test_reapplying_replaces_declared_relations(db_session: AsyncSession) -> None:
    cousin = DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="cousin")
    supervisor_id = await applied(db_session, cousin, cousin)  # duplicates are collapsed

    assert await service.is_related(db_session, supervisor_id, CONTRACTOR_PHONE)
    await service.submit_application(db_session, supervisor_id, application())
    assert not await service.is_related(db_session, supervisor_id, CONTRACTOR_PHONE)


def test_relation_phone_must_be_e164() -> None:
    with pytest.raises(ValidationError):
        DeclaredRelation(contractor_phone="08012345678", relationship="cousin")
