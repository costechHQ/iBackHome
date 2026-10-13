"""Spec rules ("Auth, roles and permissions", "API endpoints", users row) not proved elsewhere."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service
from app.base.users.models import OtpCode, RefreshToken, Role, User
from app.base.users.tests.conftest import CapturingSender, make_user, random_phone
from app.core.config import Settings
from app.core.idempotency import IdempotencyRecord

SPEC_ROLES = {"client", "contractor", "supervisor", "supplier", "ops"}


def _assert_error_shape(response: Response, status: int) -> None:
    assert response.status_code == status
    body: Any = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert all(isinstance(v, str) and v for v in body["error"].values())


# --- users table ------------------------------------------------------------------------------


async def test_users_table_has_the_spec_columns(db_session: AsyncSession) -> None:
    rows = await db_session.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
    )
    columns = {r[0] for r in rows}
    assert {"phone", "email", "full_name", "role", "status", "timezone", "country"} <= columns


def test_roles_are_exactly_the_spec_roles() -> None:
    assert {r.value for r in Role} == SPEC_ROLES


async def test_database_refuses_an_unknown_role(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(User(phone="+2348031230000", role="admin"))


# --- OTP and token lifetimes ------------------------------------------------------------------


def test_spec_defaults() -> None:
    settings = Settings()
    assert settings.otp_ttl_minutes == 5
    assert settings.otp_max_attempts == 5
    assert settings.access_token_minutes == 15
    assert settings.refresh_token_days == 30


async def test_code_is_valid_for_five_minutes(db_session: AsyncSession, sender: CapturingSender) -> None:
    phone = random_phone()
    now = datetime.now(UTC)
    await service.request_otp(db_session, phone, "203.0.113.7", sender, now=now)
    row = await db_session.scalar(select(OtpCode).where(OtpCode.identifier == "+234" + phone[1:]))
    assert row is not None
    assert row.expires_at - row.created_at == timedelta(minutes=5)


async def test_refresh_token_lasts_thirty_days(db_session: AsyncSession, sender: CapturingSender) -> None:
    phone = random_phone()
    await service.request_otp(db_session, phone, "203.0.113.7", sender)
    before = datetime.now(UTC)
    await service.verify_otp(db_session, phone, sender.last_code, now=before)
    row = await db_session.scalar(select(RefreshToken).order_by(RefreshToken.created_at.desc()).limit(1))
    assert row is not None
    assert row.expires_at - before == timedelta(days=30)


async def test_rate_limit_per_email(client: AsyncClient, sender: CapturingSender) -> None:
    email = f"rate-{random_phone()}@example.com"
    for _ in range(3):
        assert (await client.post("/api/v1/auth/otp/request", json={"identifier": email})).status_code == 202
    response = await client.post("/api/v1/auth/otp/request", json={"identifier": email})
    _assert_error_shape(response, 429)
    assert response.json()["error"]["code"] == "rate_limited"


# --- routes and Idempotency-Key ---------------------------------------------------------------


def test_auth_routes_are_under_api_v1() -> None:
    from app.main import app

    paths = app.openapi()["paths"]
    assert "post" in paths["/api/v1/auth/otp/request"]
    assert "post" in paths["/api/v1/auth/otp/verify"]
    assert "post" in paths["/api/v1/auth/refresh"]
    assert "get" in paths["/api/v1/me"]


@pytest.mark.parametrize(
    "path", ["/api/v1/auth/otp/request", "/api/v1/auth/otp/verify", "/api/v1/auth/refresh"]
)
def test_write_endpoints_accept_an_optional_idempotency_key(path: str) -> None:
    from app.main import app

    params = app.openapi()["paths"][path]["post"]["parameters"]
    header = next(p for p in params if p["name"] == "Idempotency-Key")
    assert header["in"] == "header"
    assert header["required"] is False


async def _stored_keys(db_session: AsyncSession, key: str) -> int:
    count = await db_session.scalar(
        select(func.count()).select_from(IdempotencyRecord).where(IdempotencyRecord.key == key)
    )
    return int(count or 0)


async def test_replayed_key_on_verify_never_returns_a_stored_token(
    client: AsyncClient, sender: CapturingSender, db_session: AsyncSession
) -> None:
    phone = random_phone()
    await client.post("/api/v1/auth/otp/request", json={"identifier": phone})
    body = {"identifier": phone, "code": sender.last_code}
    headers = {"Idempotency-Key": "verify-key-1"}
    first = await client.post("/api/v1/auth/otp/verify", json=body, headers=headers)
    assert first.status_code == 200
    replay = await client.post("/api/v1/auth/otp/verify", json=body, headers=headers)
    _assert_error_shape(replay, 400)
    assert "access_token" not in replay.text
    assert await _stored_keys(db_session, "verify-key-1") == 0


async def test_replayed_key_on_refresh_never_returns_a_stored_token(
    client: AsyncClient, sender: CapturingSender, db_session: AsyncSession
) -> None:
    phone = random_phone()
    await client.post("/api/v1/auth/otp/request", json={"identifier": phone})
    tokens = (
        await client.post("/api/v1/auth/otp/verify", json={"identifier": phone, "code": sender.last_code})
    ).json()
    body = {"refresh_token": tokens["refresh_token"]}
    headers = {"Idempotency-Key": "refresh-key-1"}
    first = await client.post("/api/v1/auth/refresh", json=body, headers=headers)
    assert first.status_code == 200
    replay = await client.post("/api/v1/auth/refresh", json=body, headers=headers)
    _assert_error_shape(replay, 401)
    assert "access_token" not in replay.text
    assert await _stored_keys(db_session, "refresh-key-1") == 0


# --- one error shape --------------------------------------------------------------------------


async def test_auth_errors_use_the_standard_shape(
    client: AsyncClient, sender: CapturingSender, db_session: AsyncSession
) -> None:
    _assert_error_shape(await client.post("/api/v1/auth/otp/request", json={"identifier": "+44 12"}), 422)
    _assert_error_shape(await client.post("/api/v1/auth/otp/request", json={}), 422)
    phone = random_phone()
    await client.post("/api/v1/auth/otp/request", json={"identifier": phone})
    wrong = f"{(int(sender.last_code) + 1) % 10**6:06d}"
    _assert_error_shape(
        await client.post("/api/v1/auth/otp/verify", json={"identifier": phone, "code": wrong}), 400
    )
    _assert_error_shape(await client.post("/api/v1/auth/refresh", json={"refresh_token": "x" * 43}), 401)
    _assert_error_shape(await client.get("/api/v1/me"), 401)
    suspended = await make_user(db_session, status="suspended")
    headers = {"Authorization": f"Bearer {service.create_access_token(suspended)}"}
    _assert_error_shape(await client.get("/api/v1/me", headers=headers), 403)
