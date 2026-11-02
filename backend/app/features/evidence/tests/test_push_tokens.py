"""POST /me/push-tokens and DELETE /me/push-tokens/{device_pk}: a phone's Firebase token."""

import base64
import secrets
import uuid
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications.models import PushToken
from app.base.users import service as users
from app.base.users.models import User
from app.main import app

TOKEN = "fcm-token-" + "a" * 40  # a made-up Firebase token
NO_ID = "00000000-0000-0000-0000-000000000000"


def public_key() -> str:
    der = (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    return base64.b64encode(der).decode()


async def make_user(session: AsyncSession, role: str) -> User:
    user = User(phone=f"+23480{secrets.randbelow(10**8):08d}", role=role, status="active")
    session.add(user)
    await session.flush()
    return user


def sign_in_as(user: User) -> None:
    async def fake() -> User:
        return user

    app.dependency_overrides[users.current_user] = fake


@pytest.fixture(autouse=True)
def _reset_sign_in() -> Iterator[None]:
    yield
    app.dependency_overrides.pop(users.current_user, None)


async def register(client: AsyncClient, user: User, name: str) -> str:
    """A registered device; returns its id."""
    sign_in_as(user)
    response = await client.post("/api/v1/devices", json={"device_id": name, "public_key": public_key()})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def stored(session: AsyncSession, user: User) -> list[str]:
    rows = await session.scalars(select(PushToken).where(PushToken.user_id == user.id))
    return [r.token for r in rows]


async def test_a_supervisor_saves_this_phones_token(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    device = await register(client, user, "phone-1")
    response = await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": TOKEN})
    assert response.status_code == 200, response.text
    assert response.json() == {"device_pk": device}
    assert await stored(db_session, user) == [TOKEN]


async def test_a_contractor_can_too(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "contractor")
    device = await register(client, user, "phone-c")
    response = await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": TOKEN})
    assert response.status_code == 200


async def test_a_refreshed_token_replaces_the_old_one(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    device = await register(client, user, "phone-2")
    await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": TOKEN})
    newer = "fcm-token-" + "b" * 40
    await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": newer})
    assert await stored(db_session, user) == [newer]


async def test_the_idempotency_key_replays_the_answer(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    device = await register(client, user, "phone-3")
    headers = {"Idempotency-Key": "push-token-1"}
    body = {"device_pk": device, "token": TOKEN}
    first = await client.post("/api/v1/me/push-tokens", json=body, headers=headers)
    second = await client.post("/api/v1/me/push-tokens", json=body, headers=headers)
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()


async def test_someone_elses_device_is_403_and_saves_nothing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session, "supervisor")
    thief = await make_user(db_session, "contractor")
    device = await register(client, owner, "phone-4")
    sign_in_as(thief)
    response = await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": TOKEN})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_device_owner"
    assert await stored(db_session, thief) == []
    assert await stored(db_session, owner) == []


async def test_an_unknown_device_is_404(client: AsyncClient, db_session: AsyncSession) -> None:
    sign_in_as(await make_user(db_session, "supervisor"))
    response = await client.post("/api/v1/me/push-tokens", json={"device_pk": NO_ID, "token": TOKEN})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "device_not_found"


async def test_a_revoked_device_cannot_get_push(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    device = await register(client, user, "phone-5")
    await client.post(f"/api/v1/devices/{device}/revoke")
    response = await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": TOKEN})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "device_revoked"


async def test_revoking_a_phone_forgets_its_token(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    device = await register(client, user, "phone-6")
    await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": TOKEN})
    assert await stored(db_session, user) == [TOKEN]
    await client.post(f"/api/v1/devices/{device}/revoke")
    assert await stored(db_session, user) == []


async def test_signing_out_removes_the_token(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    device = await register(client, user, "phone-7")
    await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": TOKEN})
    response = await client.delete(f"/api/v1/me/push-tokens/{device}")
    assert response.status_code == 204
    assert await stored(db_session, user) == []
    assert (await client.delete(f"/api/v1/me/push-tokens/{device}")).status_code == 204  # twice is fine


async def test_removing_someone_elses_token_is_403_and_leaves_it(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session, "supervisor")
    other = await make_user(db_session, "contractor")
    device = await register(client, owner, "phone-8")
    await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": TOKEN})
    sign_in_as(other)
    response = await client.delete(f"/api/v1/me/push-tokens/{device}")
    assert response.status_code == 403
    assert await stored(db_session, owner) == [TOKEN]


@pytest.mark.parametrize("role", ["client", "ops", "supplier"])
async def test_only_the_app_roles_can_register_a_token(
    client: AsyncClient, db_session: AsyncSession, role: str
) -> None:
    sign_in_as(await make_user(db_session, role))
    response = await client.post(
        "/api/v1/me/push-tokens", json={"device_pk": str(uuid.uuid4()), "token": TOKEN}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"


@pytest.mark.parametrize("token", ["", "short", "x" * 5000])
async def test_a_token_that_is_too_short_or_too_long_is_422(
    client: AsyncClient, db_session: AsyncSession, token: str
) -> None:
    user = await make_user(db_session, "supervisor")
    device = await register(client, user, "phone-9")
    response = await client.post("/api/v1/me/push-tokens", json={"device_pk": device, "token": token})
    assert response.status_code == 422


async def test_signed_out_is_401(client: AsyncClient) -> None:
    body = {"device_pk": NO_ID, "token": TOKEN}
    assert (await client.post("/api/v1/me/push-tokens", json=body)).status_code == 401
    assert (await client.delete(f"/api/v1/me/push-tokens/{NO_ID}")).status_code == 401
