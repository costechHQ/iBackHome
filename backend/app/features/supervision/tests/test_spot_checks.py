"""Spot-check rules (service.py). Needs Postgres (backend/conftest.py)."""

import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.core.errors import AppError
from app.features.supervision import service
from app.features.supervision.schemas import DeclaredRelation
from app.features.supervision.tests.factories import application, approval, make_user

PROJECT_ID = uuid.uuid4()
CONTRACTOR_PHONE = "+2348012345678"
TOMORROW = datetime.now(UTC) + timedelta(days=1)


async def test_ops_schedules_a_spot_check_stored_in_utc(
    db_session: AsyncSession, vetted: User, ops: User
) -> None:
    lagos_9am = datetime.now(timezone(timedelta(hours=1))).replace(microsecond=0) + timedelta(days=2)

    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, vetted.id, lagos_9am, ops.id)

    assert spot_check.scheduled_for == lagos_9am
    assert spot_check.scheduled_for.utcoffset() == timedelta(0)
    assert (spot_check.completed_at, spot_check.findings, spot_check.scheduled_by) == (None, None, ops.id)
    assert await service.list_my_spot_checks(db_session, vetted.id) == [spot_check]


async def test_spot_check_in_the_past_is_refused(db_session: AsyncSession, vetted: User, ops: User) -> None:
    with pytest.raises(AppError) as error:
        await service.schedule_spot_check(
            db_session, PROJECT_ID, vetted.id, datetime.now(UTC) - timedelta(hours=1), ops.id
        )

    assert (error.value.code, error.value.status_code) == ("spot_check_in_past", 422)


async def test_unvetted_supervisor_cannot_do_a_spot_check(
    db_session: AsyncSession, applicant: User, ops: User
) -> None:
    with pytest.raises(AppError) as error:
        await service.schedule_spot_check(db_session, PROJECT_ID, applicant.id, TOMORROW, ops.id)

    assert error.value.code == "supervisor_not_vetted"


async def test_project_supervisor_cannot_spot_check_their_own_project(
    db_session: AsyncSession, vetted: User, ops: User
) -> None:
    with pytest.raises(AppError) as error:
        await service.schedule_spot_check(
            db_session, PROJECT_ID, vetted.id, TOMORROW, ops.id, assigned_supervisor_id=vetted.id
        )

    assert (error.value.code, error.value.status_code) == ("spot_check_by_assigned_supervisor", 409)


async def test_supervisor_related_to_the_contractor_cannot_spot_check(
    db_session: AsyncSession, ops: User
) -> None:
    visitor = await make_user(db_session, "supervisor")
    uncle = DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="uncle")
    await service.submit_application(db_session, visitor.id, application(uncle))
    await service.vet(db_session, visitor.id, approval(), ops.id)

    with pytest.raises(AppError) as error:
        await service.schedule_spot_check(
            db_session, PROJECT_ID, visitor.id, TOMORROW, ops.id, contractor_phone=CONTRACTOR_PHONE
        )

    assert error.value.code == "supervisor_related_to_contractor"


@pytest.mark.parametrize("role", ["contractor", "client", "supervisor", "supplier"])
async def test_only_ops_sees_a_projects_spot_checks(
    db_session: AsyncSession, vetted: User, ops: User, role: str
) -> None:
    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, vetted.id, TOMORROW, ops.id)

    assert await service.list_project_spot_checks(db_session, PROJECT_ID, "ops") == [spot_check]
    with pytest.raises(AppError) as error:
        await service.list_project_spot_checks(db_session, PROJECT_ID, role)
    assert (error.value.code, error.value.status_code) == ("spot_checks_hidden", 403)


async def test_visiting_supervisor_completes_with_findings(
    db_session: AsyncSession, vetted: User, ops: User
) -> None:
    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, vetted.id, TOMORROW, ops.id)

    done = await service.complete_spot_check(
        db_session, spot_check.id, vetted.id, "Blockwork matches the claim."
    )

    assert done.findings == "Blockwork matches the claim."
    assert done.completed_at is not None
    assert await service.list_my_spot_checks(db_session, vetted.id) == []


async def test_spot_check_cannot_be_completed_twice(
    db_session: AsyncSession, vetted: User, ops: User
) -> None:
    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, vetted.id, TOMORROW, ops.id)
    await service.complete_spot_check(db_session, spot_check.id, vetted.id, "All good on site today.")

    with pytest.raises(AppError) as error:
        await service.complete_spot_check(db_session, spot_check.id, vetted.id, "Trying to overwrite it.")

    assert (error.value.code, error.value.status_code) == ("spot_check_already_completed", 409)


async def test_another_supervisor_cannot_complete_it(
    db_session: AsyncSession, vetted: User, ops: User
) -> None:
    someone_else = await make_user(db_session, "supervisor")
    spot_check = await service.schedule_spot_check(db_session, PROJECT_ID, vetted.id, TOMORROW, ops.id)

    with pytest.raises(AppError) as error:
        await service.complete_spot_check(db_session, spot_check.id, someone_else.id, "Not my visit at all.")

    assert (error.value.code, error.value.status_code) == ("spot_check_not_found", 404)
