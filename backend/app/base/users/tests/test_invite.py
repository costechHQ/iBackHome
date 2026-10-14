"""invite_contractor(): the account a project's contractor invite lands on."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service
from app.base.users.models import User
from app.base.users.tests.conftest import random_phone
from app.core.errors import AppError


async def test_new_number_becomes_an_active_contractor(db_session: AsyncSession) -> None:
    phone = random_phone()
    user = await service.invite_contractor(db_session, phone)
    assert (user.phone, user.role, user.status) == ("+234" + phone[1:], "contractor", "active")


async def test_existing_contractor_is_returned(db_session: AsyncSession) -> None:
    existing = await service.invite_contractor(db_session, random_phone())
    assert existing.phone is not None
    assert (await service.invite_contractor(db_session, existing.phone)).id == existing.id


async def test_invited_contractor_signs_in_to_the_same_account(db_session: AsyncSession) -> None:
    phone = random_phone()
    invited = await service.invite_contractor(db_session, phone)
    signed_in = await service._find_or_create_user(db_session, "+234" + phone[1:], "sms")
    assert signed_in.id == invited.id
    assert signed_in.role == "contractor"


@pytest.mark.parametrize("role", ["client", "supervisor", "supplier", "ops"])
async def test_other_roles_are_409_and_unchanged(db_session: AsyncSession, role: str) -> None:
    other = User(phone="+234" + random_phone()[1:], role=role)
    db_session.add(other)
    await db_session.flush()
    assert other.phone is not None
    with pytest.raises(AppError) as caught:
        await service.invite_contractor(db_session, other.phone)
    assert (caught.value.code, caught.value.status_code) == ("role_conflict", 409)
    assert other.role == role


async def test_email_is_refused(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as caught:
        await service.invite_contractor(db_session, "builder@example.com")
    assert (caught.value.code, caught.value.status_code) == ("invalid_phone", 422)
