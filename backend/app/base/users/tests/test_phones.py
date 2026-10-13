"""Phone numbers from any country, and the sms / whatsapp / email channels."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service
from app.base.users.models import User
from app.base.users.tests.conftest import CapturingSender

REQUEST = "/api/v1/auth/otp/request"
VERIFY = "/api/v1/auth/otp/verify"


async def _sign_in(
    client: AsyncClient, sender: CapturingSender, identifier: str, **extra: str
) -> tuple[str, str]:
    """Request and verify a code; returns (user id, access token)."""
    response = await client.post(REQUEST, json={"identifier": identifier, **extra})
    assert response.status_code == 202, response.json()
    response = await client.post(VERIFY, json={"identifier": identifier, "code": sender.last_code})
    assert response.status_code == 200, response.json()
    token = str(response.json()["access_token"])
    return str(service.decode_access_token(token)), token


def _assert_422(response_json: dict[str, dict[str, str]], code: str) -> str:
    assert set(response_json) == {"error"}
    assert set(response_json["error"]) == {"code", "message"}
    assert response_json["error"]["code"] == code
    return response_json["error"]["message"]


@pytest.mark.parametrize(
    ("typed", "e164"),
    [
        ("0803 123 4567", "+2348031234567"),  # Nigerian local
        ("+234 803 123 4567", "+2348031234567"),  # Nigerian international
        ("+44 7400 123456", "+447400123456"),  # UK
        ("+1 201 555 0123", "+12015550123"),  # US
        ("+49 1512 3456789", "+4915123456789"),  # Germany
    ],
)
def test_numbers_from_any_country_become_e164(typed: str, e164: str) -> None:
    assert service.normalise_identifier(typed) == (e164, "sms")


@pytest.mark.parametrize("number", ["+44 7400 123456", "+1 201 555 0123", "+49 1512 3456789"])
async def test_foreign_numbers_can_sign_in(client: AsyncClient, sender: CapturingSender, number: str) -> None:
    _, token = await _sign_in(client, sender, number)
    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["phone"] == service.normalise_identifier(number)[0]


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("0803 123 4567", "+2348031234567"),
        ("+44 7400 123456", "+447400123456"),
    ],
)
async def test_one_number_typed_two_ways_is_one_account(
    client: AsyncClient, sender: CapturingSender, first: str, second: str
) -> None:
    first_id, _ = await _sign_in(client, sender, first)
    second_id, _ = await _sign_in(client, sender, second)
    assert first_id == second_id


async def test_invalid_number_is_422(client: AsyncClient, sender: CapturingSender) -> None:
    response = await client.post(REQUEST, json={"identifier": "+44 12"})
    assert response.status_code == 422
    _assert_422(response.json(), "invalid_phone")
    assert sender.sent == []


async def test_foreign_number_without_plus_is_422_asking_for_country_code(
    client: AsyncClient, sender: CapturingSender
) -> None:
    response = await client.post(REQUEST, json={"identifier": "447400123456"})
    assert response.status_code == 422
    message = _assert_422(response.json(), "phone_needs_country_code")
    assert "country code" in message
    assert sender.sent == []


@pytest.mark.parametrize("channel", ["sms", "whatsapp"])
async def test_foreign_number_works_by_sms_and_whatsapp(
    client: AsyncClient, sender: CapturingSender, channel: str
) -> None:
    await _sign_in(client, sender, "+44 7400 123456", channel=channel)
    assert sender.sent[-1][:2] == ("+447400123456", channel)


async def test_phone_defaults_to_sms_and_email_to_email(client: AsyncClient, sender: CapturingSender) -> None:
    await client.post(REQUEST, json={"identifier": "+1 201 555 0123"})
    await client.post(REQUEST, json={"identifier": "ada@example.com"})
    assert [channel for _, channel, _ in sender.sent] == ["sms", "email"]


@pytest.mark.parametrize(
    ("identifier", "channel"),
    [
        ("ada@example.com", "sms"),
        ("ada@example.com", "whatsapp"),
        ("+44 7400 123456", "email"),
        ("0803 123 4567", "email"),
    ],
)
async def test_channel_mismatch_is_422(
    client: AsyncClient, sender: CapturingSender, identifier: str, channel: str
) -> None:
    response = await client.post(REQUEST, json={"identifier": identifier, "channel": channel})
    assert response.status_code == 422
    _assert_422(response.json(), "channel_mismatch")
    assert sender.sent == []


async def test_unknown_channel_is_422(client: AsyncClient) -> None:
    response = await client.post(REQUEST, json={"identifier": "0803 123 4567", "channel": "fax"})
    assert response.status_code == 422
    _assert_422(response.json(), "validation_error")


async def test_whatsapp_channel_finds_and_creates_users_by_phone(db_session: AsyncSession) -> None:
    created = await service._find_or_create_user(db_session, "+447400123456", "whatsapp")
    assert created.phone == "+447400123456"
    assert created.email is None
    found = await service._find_or_create_user(db_session, "+447400123456", "whatsapp")
    assert found.id == created.id


async def test_whatsapp_login_creates_one_user_by_phone(
    client: AsyncClient, sender: CapturingSender, db_session: AsyncSession
) -> None:
    await _sign_in(client, sender, "+44 7400 123456", channel="whatsapp")
    users = (await db_session.scalars(select(User).where(User.phone == "+447400123456"))).all()
    assert len(users) == 1
    assert users[0].email is None
