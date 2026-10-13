"""Access tokens and refresh-token rotation."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service
from app.base.users.models import RefreshToken
from app.base.users.schemas import TokenPair
from app.base.users.tests.conftest import CapturingSender, make_user, random_phone
from app.core.config import get_settings
from app.core.errors import AppError


async def _sign_in(session: AsyncSession, sender: CapturingSender, phone: str | None = None) -> TokenPair:
    phone = phone or random_phone()
    await service.request_otp(session, phone, "203.0.113.7", sender)
    return await service.verify_otp(session, phone, sender.last_code)


async def test_access_token_claims_and_lifetime(db_session: AsyncSession) -> None:
    user = await make_user(db_session, role="supervisor")
    now = datetime.now(UTC)
    token = service.create_access_token(user, now=now)
    claims = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"], issuer="ibackhome")
    assert claims["sub"] == str(user.id)
    assert claims["role"] == "supervisor"
    assert claims["type"] == "access"
    assert claims["exp"] - claims["iat"] == 15 * 60


async def test_refresh_token_is_stored_only_as_a_hash(
    db_session: AsyncSession, sender: CapturingSender
) -> None:
    tokens = await _sign_in(db_session, sender)
    hashes = (await db_session.scalars(select(RefreshToken.token_hash))).all()
    assert tokens.refresh_token not in hashes
    assert len(hashes[-1]) == 64


async def test_refresh_rotates_the_token(client: AsyncClient, sender: CapturingSender) -> None:
    phone = random_phone()
    await client.post("/api/v1/auth/otp/request", json={"identifier": phone})
    first = (
        await client.post("/api/v1/auth/otp/verify", json={"identifier": phone, "code": sender.last_code})
    ).json()

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]
    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {second['access_token']}"})
    assert me.status_code == 200

    # The old refresh token is used up.
    again = await client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert again.status_code == 401
    assert again.json()["error"]["code"] == "refresh_token_reused"


async def test_reusing_an_old_token_signs_the_user_out_everywhere(
    db_session: AsyncSession, sender: CapturingSender
) -> None:
    first = await _sign_in(db_session, sender)
    second = await service.rotate_refresh_token(db_session, first.refresh_token)

    with pytest.raises(AppError) as err:
        await service.rotate_refresh_token(db_session, first.refresh_token)  # a copied old token
    assert (err.value.status_code, err.value.code) == (401, "refresh_token_reused")

    # Even the newest token no longer works.
    with pytest.raises(AppError) as err:
        await service.rotate_refresh_token(db_session, second.refresh_token)
    assert err.value.status_code == 401


async def test_expired_refresh_token_is_refused(db_session: AsyncSession, sender: CapturingSender) -> None:
    tokens = await _sign_in(db_session, sender)
    later = datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days, seconds=1)
    with pytest.raises(AppError) as err:
        await service.rotate_refresh_token(db_session, tokens.refresh_token, now=later)
    assert (err.value.status_code, err.value.code) == (401, "invalid_refresh_token")


async def test_unknown_refresh_token_is_refused(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "x" * 43})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"


async def test_suspended_user_cannot_refresh(db_session: AsyncSession, sender: CapturingSender) -> None:
    user = await make_user(db_session)
    assert user.phone is not None
    tokens = await _sign_in(db_session, sender, user.phone)
    user.status = "suspended"
    await db_session.flush()
    with pytest.raises(AppError) as err:
        await service.rotate_refresh_token(db_session, tokens.refresh_token)
    assert (err.value.status_code, err.value.code) == (403, "account_suspended")
