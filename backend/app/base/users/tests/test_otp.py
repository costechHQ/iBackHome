"""Requesting and verifying login codes."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications.adapters import FakeAdapter
from app.base.notifications.models import Channel, Notification
from app.base.users import otp_sender, service
from app.base.users.models import OtpCode, User
from app.base.users.otp_sender import NotificationSender
from app.base.users.tests.conftest import CapturingSender, make_user, random_phone
from app.core.config import Settings, get_settings
from app.core.errors import AppError

IP = "203.0.113.7"


async def _request(session: AsyncSession, sender: CapturingSender, identifier: str, **kw: object) -> str:
    await service.request_otp(session, identifier, kw.pop("ip", IP), sender, **kw)  # type: ignore[arg-type]
    return sender.last_code


async def _code_row(session: AsyncSession, identifier: str) -> OtpCode:
    row = await session.scalar(
        select(OtpCode).where(OtpCode.identifier == identifier).order_by(OtpCode.created_at.desc()).limit(1)
    )
    assert row is not None
    return row


def _wrong(code: str) -> str:
    return f"{(int(code) + 1) % 10**6:06d}"


# --- identifiers --------------------------------------------------------------------------------


def test_nigerian_local_number_becomes_e164() -> None:
    assert service.normalise_identifier("0803 123 4567") == ("+2348031234567", "sms")
    assert service.normalise_identifier("+234 803 123 4567") == ("+2348031234567", "sms")


def test_email_is_lower_cased() -> None:
    assert service.normalise_identifier("  Ada.Obi@Example.COM ") == ("ada.obi@example.com", "email")


@pytest.mark.parametrize(
    ("bad", "code"),
    [
        ("12345", "invalid_phone"),
        ("0803", "invalid_phone"),
        ("not-a-phone", "invalid_phone"),
        ("+44 12", "invalid_phone"),
        ("a@b", "invalid_email"),
        ("a@@b.com", "invalid_email"),
        ("@example.com", "invalid_email"),
        ("a b@x.com", "invalid_email"),
    ],
)
def test_invalid_identifiers_are_refused(bad: str, code: str) -> None:
    with pytest.raises(AppError) as err:
        service.normalise_identifier(bad)
    assert err.value.status_code == 422
    assert err.value.code == code


# --- requesting a code ------------------------------------------------------------------------


async def test_request_sends_a_six_digit_code_and_stores_only_its_hash(
    db_session: AsyncSession, sender: CapturingSender
) -> None:
    phone = random_phone()
    code = await _request(db_session, sender, phone)
    identifier = "+234" + phone[1:]
    assert sender.sent == [(identifier, "sms", code)]
    assert len(code) == 6 and code.isdigit()
    row = await _code_row(db_session, identifier)
    assert code not in row.code_hash
    assert row.attempts == 0
    assert row.requested_ip == IP


async def test_new_request_retires_the_previous_code(
    db_session: AsyncSession, sender: CapturingSender
) -> None:
    phone = random_phone()
    first = await _request(db_session, sender, phone)
    second = await _request(db_session, sender, phone)
    if first == second:  # 1-in-a-million: the two random codes happen to match
        pytest.skip("random codes collided")
    with pytest.raises(AppError) as err:
        await service.verify_otp(db_session, phone, first)
    assert err.value.code == "invalid_code"
    tokens = await service.verify_otp(db_session, phone, second)
    assert tokens.access_token


async def test_rate_limit_per_phone(client: AsyncClient, sender: CapturingSender) -> None:
    phone = random_phone()
    for _ in range(get_settings().otp_limit_per_identifier):
        assert (await client.post("/api/v1/auth/otp/request", json={"identifier": phone})).status_code == 202
    response = await client.post("/api/v1/auth/otp/request", json={"identifier": phone})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert int(response.headers["Retry-After"]) > 0
    assert len(sender.sent) == get_settings().otp_limit_per_identifier


async def test_rate_limit_per_ip(
    db_session: AsyncSession, sender: CapturingSender, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "otp_limit_per_ip", 2)
    await _request(db_session, sender, random_phone())
    await _request(db_session, sender, random_phone())
    with pytest.raises(Exception) as err:
        await _request(db_session, sender, random_phone())
    assert getattr(err.value, "status_code", None) == 429
    # Another IP is not affected.
    await _request(db_session, sender, random_phone(), ip="198.51.100.9")


async def test_rate_limit_resets_after_the_window(db_session: AsyncSession, sender: CapturingSender) -> None:
    phone = random_phone()
    start = datetime.now(UTC)
    for _ in range(get_settings().otp_limit_per_identifier):
        await _request(db_session, sender, phone, now=start)
    later = start + timedelta(minutes=get_settings().otp_limit_window_minutes, seconds=1)
    await _request(db_session, sender, phone, now=later)  # allowed again


async def test_same_idempotency_key_replays_without_a_second_code(
    client: AsyncClient, sender: CapturingSender
) -> None:
    body = {"identifier": random_phone()}
    headers = {"Idempotency-Key": "otp-request-1"}
    first = await client.post("/api/v1/auth/otp/request", json=body, headers=headers)
    second = await client.post("/api/v1/auth/otp/request", json=body, headers=headers)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json() == {"status": "sent", "expires_in": 300}
    assert len(sender.sent) == 1


async def test_invalid_identifier_is_422(client: AsyncClient, sender: CapturingSender) -> None:
    response = await client.post("/api/v1/auth/otp/request", json={"identifier": "not-a-phone"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_phone"
    assert sender.sent == []


# --- verifying a code -------------------------------------------------------------------------


async def test_unknown_person_signs_up_as_client(client: AsyncClient, sender: CapturingSender) -> None:
    phone = random_phone()
    await client.post("/api/v1/auth/otp/request", json={"identifier": phone})
    response = await client.post(
        "/api/v1/auth/otp/verify", json={"identifier": phone, "code": sender.last_code}
    )
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    tokens = response.json()
    assert tokens["token_type"] == "bearer" and tokens["expires_in"] == 900  # noqa: S105 - not a secret
    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["phone"] == "+234" + phone[1:]
    assert me.json()["role"] == "client"


async def test_email_login_works(db_session: AsyncSession, sender: CapturingSender) -> None:
    email = f"client-{random_phone()}@Example.com"
    code = await _request(db_session, sender, email)
    assert sender.sent[-1][1] == "email"
    await service.verify_otp(db_session, email, code)
    user = await db_session.scalar(select(User).where(User.email == email.lower()))
    assert user is not None and user.role == "client"


async def test_existing_contractor_keeps_their_role(
    db_session: AsyncSession, sender: CapturingSender
) -> None:
    contractor = await make_user(db_session, role="contractor")
    assert contractor.phone is not None
    code = await _request(db_session, sender, contractor.phone)
    tokens = await service.verify_otp(db_session, contractor.phone, code)
    assert service.decode_access_token(tokens.access_token) == contractor.id
    count = len((await db_session.scalars(select(User).where(User.phone == contractor.phone))).all())
    assert count == 1


async def test_expired_code_is_refused(db_session: AsyncSession, sender: CapturingSender) -> None:
    phone = random_phone()
    start = datetime.now(UTC)
    code = await _request(db_session, sender, phone, now=start)
    later = start + timedelta(minutes=get_settings().otp_ttl_minutes, seconds=1)
    with pytest.raises(AppError) as err:
        await service.verify_otp(db_session, phone, code, now=later)
    assert (err.value.status_code, err.value.code) == (400, "otp_expired")


async def test_wrong_code_is_refused_and_counted(db_session: AsyncSession, sender: CapturingSender) -> None:
    phone = random_phone()
    code = await _request(db_session, sender, phone)
    with pytest.raises(AppError) as err:
        await service.verify_otp(db_session, phone, _wrong(code))
    assert (err.value.status_code, err.value.code) == (400, "invalid_code")
    assert (await _code_row(db_session, "+234" + phone[1:])).attempts == 1


async def test_too_many_attempts_kills_the_code_even_for_the_right_digits(
    db_session: AsyncSession, sender: CapturingSender
) -> None:
    phone = random_phone()
    code = await _request(db_session, sender, phone)
    for _ in range(get_settings().otp_max_attempts):
        with pytest.raises(AppError) as err:
            await service.verify_otp(db_session, phone, _wrong(code))
        assert err.value.code == "invalid_code"
    with pytest.raises(AppError) as err:
        await service.verify_otp(db_session, phone, code)
    assert (err.value.status_code, err.value.code) == (429, "too_many_attempts")
    # A new code is needed; it works (and is itself subject to the rate limit).
    new_code = await _request(db_session, sender, phone)
    assert (await service.verify_otp(db_session, phone, new_code)).access_token


async def test_code_can_be_used_only_once(db_session: AsyncSession, sender: CapturingSender) -> None:
    phone = random_phone()
    code = await _request(db_session, sender, phone)
    await service.verify_otp(db_session, phone, code)
    with pytest.raises(AppError) as err:
        await service.verify_otp(db_session, phone, code)
    assert err.value.code == "invalid_code"


async def test_suspended_user_cannot_sign_in(db_session: AsyncSession, sender: CapturingSender) -> None:
    user = await make_user(db_session, status="suspended")
    assert user.phone is not None
    code = await _request(db_session, sender, user.phone)
    with pytest.raises(AppError) as err:
        await service.verify_otp(db_session, user.phone, code)
    assert (err.value.status_code, err.value.code) == (403, "account_suspended")


async def test_code_must_be_six_digits(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/verify", json={"identifier": random_phone(), "code": "12ab"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# --- sending the code through notifications ------------------------------------------------------


@pytest.mark.parametrize(
    ("identifier", "channel"),
    [("+2348031234567", "sms"), ("+447700900123", "whatsapp"), ("ada@example.com", "email")],
)
async def test_code_goes_out_on_the_chosen_channel(
    db_session: AsyncSession, identifier: str, channel: str
) -> None:
    fakes = {c: FakeAdapter() for c in Channel}
    await NotificationSender(db_session, adapters=fakes).send(identifier, channel, "482913")

    [(to, message)] = fakes[Channel(channel)].sent
    assert to == identifier
    assert message.template == "auth.login_code"
    assert "482913" in message.text
    assert sum(len(f.sent) for f in fakes.values()) == 1  # that channel only, no fallback
    row = await db_session.scalar(
        select(Notification)
        .where(Notification.recipient == identifier)
        .order_by(Notification.created_at.desc())
        .limit(1)
    )
    assert row is not None and row.payload == {}  # the code is never stored


async def test_unconfigured_channel_refuses_with_503(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as err:
        await NotificationSender(db_session, adapters={}).send("+2348031234567", "sms", "123456")
    assert (err.value.status_code, err.value.code) == (503, "notifications_not_configured")


async def test_provider_failure_refuses_with_502(db_session: AsyncSession) -> None:
    failing = {Channel.SMS: FakeAdapter(fail=True)}
    with pytest.raises(AppError) as err:
        await NotificationSender(db_session, adapters=failing).send("+2348031234567", "sms", "123456")
    assert (err.value.status_code, err.value.code) == (502, "notification_failed")


async def test_request_route_fails_when_the_code_cannot_be_sent(client: AsyncClient) -> None:
    """Without the test's capturing sender, the route uses notifications for real."""
    from app.main import app

    app.dependency_overrides[otp_sender.get_otp_sender] = lambda: _Refusing()
    try:
        response = await client.post("/api/v1/auth/otp/request", json={"identifier": random_phone()})
    finally:
        app.dependency_overrides.pop(otp_sender.get_otp_sender, None)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "notifications_not_configured"


class _Refusing:
    async def send(self, identifier: str, channel: str, code: str) -> None:
        raise AppError("notifications_not_configured", "Messages can't be sent by sms here yet.", 503)


def test_placeholder_jwt_secret_is_refused_outside_local() -> None:
    for secret in ("change-me", "change-me-to-a-long-random-string", "short"):
        with pytest.raises(ValidationError):
            Settings(environment="production", jwt_secret=secret)
    assert Settings(environment="production", jwt_secret="x" * 32).environment == "production"
    # A deliberately fake placeholder: local development may keep it.
    local = Settings(environment="local", jwt_secret="change-me")  # noqa: S106 - test value
    assert local.environment == "local"
