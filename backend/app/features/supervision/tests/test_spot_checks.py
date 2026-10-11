"""Spot-check rules (service.py). Needs Postgres; see conftest.py."""

import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.supervision import service
from app.features.supervision.schemas import DeclaredRelation, SupervisorApplication, VettingDecision

PROJECT_ID = uuid.uuid4()
OPS_ID = uuid.uuid4()
CONTRACTOR_PHONE = "+2348012345678"
TOMORROW = datetime.now(UTC) + timedelta(days=1)


async def vetted_supervisor(session: AsyncSession, *relations: DeclaredRelation) -> uuid.UUID:
    supervisor_id = uuid.uuid4()
    await service.submit_application(
        session,
        supervisor_id,
        SupervisorApplication(
            registration_body="NIOB",
            registration_no="B.777",
            guarantor_1="Ada Obi, +2348031111111",
            guarantor_2="Uche Ani, +2348032222222",
            related_contractors=list(relations),
        ),
    )
    decision = VettingDecision(
        decision="approved",
        registration_verified=True,
        nin_verified=True,
        guarantor_1_verified=True,
        guarantor_2_verified=True,
    )
    await service.vet(session, supervisor_id, decision, OPS_ID)
    return supervisor_id


async def test_ops_schedules_a_spot_check_stored_in_utc(db_session: AsyncSession) -> None:
    visitor = await vetted_supervisor(db_session)
    lagos_9am = datetime.now(timezone(timedelta(hours=1))).replace(microsecond=0) + timedelta(days=2)

    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, visitor, lagos_9am, OPS_ID)

    assert spot_check.scheduled_for == lagos_9am
    assert spot_check.scheduled_for.utcoffset() == timedelta(0)
    assert (spot_check.completed_at, spot_check.findings) == (None, None)
    assert await service.list_my_spot_checks(db_session, visitor) == [spot_check]


async def test_spot_check_in_the_past_is_refused(db_session: AsyncSession) -> None:
    visitor = await vetted_supervisor(db_session)

    with pytest.raises(AppError) as error:
        await service.schedule_spot_check(
            db_session, PROJECT_ID, visitor, datetime.now(UTC) - timedelta(hours=1), OPS_ID
        )

    assert (error.value.code, error.value.status_code) == ("spot_check_in_past", 422)


async def test_unvetted_supervisor_cannot_do_a_spot_check(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await service.schedule_spot_check(db_session, PROJECT_ID, uuid.uuid4(), TOMORROW, OPS_ID)

    assert error.value.code == "supervisor_not_vetted"


async def test_project_supervisor_cannot_spot_check_their_own_project(db_session: AsyncSession) -> None:
    assigned = await vetted_supervisor(db_session)

    with pytest.raises(AppError) as error:
        await service.schedule_spot_check(
            db_session, PROJECT_ID, assigned, TOMORROW, OPS_ID, assigned_supervisor_id=assigned
        )

    assert (error.value.code, error.value.status_code) == ("spot_check_by_assigned_supervisor", 409)


async def test_supervisor_related_to_the_contractor_cannot_spot_check(db_session: AsyncSession) -> None:
    visitor = await vetted_supervisor(
        db_session, DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="uncle")
    )

    with pytest.raises(AppError) as error:
        await service.schedule_spot_check(
            db_session, PROJECT_ID, visitor, TOMORROW, OPS_ID, contractor_phone=CONTRACTOR_PHONE
        )

    assert error.value.code == "supervisor_related_to_contractor"


@pytest.mark.parametrize("role", ["contractor", "client", "supervisor", "supplier"])
async def test_only_ops_sees_a_projects_spot_checks(db_session: AsyncSession, role: str) -> None:
    visitor = await vetted_supervisor(db_session)
    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, visitor, TOMORROW, OPS_ID)

    assert await service.list_project_spot_checks(db_session, PROJECT_ID, "ops") == [spot_check]
    with pytest.raises(AppError) as error:
        await service.list_project_spot_checks(db_session, PROJECT_ID, role)
    assert (error.value.code, error.value.status_code) == ("spot_checks_hidden", 403)


async def test_visiting_supervisor_completes_with_findings(db_session: AsyncSession) -> None:
    visitor = await vetted_supervisor(db_session)
    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, visitor, TOMORROW, OPS_ID)

    done = await service.complete_spot_check(
        db_session, spot_check.id, visitor, "Blockwork matches the claim."
    )

    assert done.findings == "Blockwork matches the claim."
    assert done.completed_at is not None
    assert await service.list_my_spot_checks(db_session, visitor) == []


async def test_spot_check_cannot_be_completed_twice(db_session: AsyncSession) -> None:
    visitor = await vetted_supervisor(db_session)
    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, visitor, TOMORROW, OPS_ID)
    await service.complete_spot_check(db_session, spot_check.id, visitor, "All good on site today.")

    with pytest.raises(AppError) as error:
        await service.complete_spot_check(db_session, spot_check.id, visitor, "Trying to overwrite it.")

    assert (error.value.code, error.value.status_code) == ("spot_check_already_completed", 409)


async def test_another_supervisor_cannot_complete_it(db_session: AsyncSession) -> None:
    visitor = await vetted_supervisor(db_session)
    someone_else = await vetted_supervisor(db_session)
    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, visitor, TOMORROW, OPS_ID)

    with pytest.raises(AppError) as error:
        await service.complete_spot_check(db_session, spot_check.id, someone_else, "Not my visit at all.")

    assert (error.value.code, error.value.status_code) == ("spot_check_not_found", 404)
