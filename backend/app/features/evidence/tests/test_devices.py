import base64
import secrets
import uuid
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.base.users.models import User
from app.core.errors import AppError
from app.features.evidence import service
from app.main import app


def public_key(curve: ec.EllipticCurve | None = None) -> str:
    private = ec.generate_private_key(curve or ec.SECP256R1())
    der = private.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
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


@pytest.fixture
async def supervisor(db_session: AsyncSession) -> User:
    return await make_user(db_session, "supervisor")


@pytest.fixture
async def contractor(db_session: AsyncSession) -> User:
    return await make_user(db_session, "contractor")


@pytest.fixture
async def ops(db_session: AsyncSession) -> User:
    return await make_user(db_session, "ops")


# POST /devices


async def test_supervisor_registers_a_device(client: AsyncClient, supervisor: User) -> None:
    sign_in_as(supervisor)
    key = public_key()
    response = await client.post("/api/v1/devices", json={"device_id": "phone-1", "public_key": key})
    assert response.status_code == 201
    body = response.json()
    assert body["device_id"] == "phone-1"
    assert body["public_key"] == key
    assert body["user_id"] == str(supervisor.id)
    assert body["revoked_at"] is None


async def test_contractor_can_register_too(client: AsyncClient, contractor: User) -> None:
    sign_in_as(contractor)
    response = await client.post("/api/v1/devices", json={"device_id": "phone-c", "public_key": public_key()})
    assert response.status_code == 201


@pytest.mark.parametrize("role", ["client", "ops", "supplier"])
async def test_other_roles_are_forbidden(client: AsyncClient, db_session: AsyncSession, role: str) -> None:
    sign_in_as(await make_user(db_session, role))
    response = await client.post("/api/v1/devices", json={"device_id": "phone-x", "public_key": public_key()})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"


async def test_signed_out_is_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/devices", json={"device_id": "phone-x", "public_key": public_key()})
    assert response.status_code == 401


async def test_same_device_and_key_again_returns_the_existing_row(
    client: AsyncClient, supervisor: User
) -> None:
    sign_in_as(supervisor)
    payload = {"device_id": "phone-2", "public_key": public_key()}
    first = await client.post("/api/v1/devices", json=payload)
    second = await client.post("/api/v1/devices", json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


async def test_idempotency_key_replays_the_saved_response(client: AsyncClient, supervisor: User) -> None:
    sign_in_as(supervisor)
    payload = {"device_id": "phone-3", "public_key": public_key()}
    headers = {"Idempotency-Key": "register-phone-3"}
    first = await client.post("/api/v1/devices", json=payload, headers=headers)
    second = await client.post("/api/v1/devices", json=payload, headers=headers)
    assert first.status_code == second.status_code == 201
    assert second.json() == first.json()


async def test_device_id_with_another_key_is_a_conflict(client: AsyncClient, supervisor: User) -> None:
    sign_in_as(supervisor)
    await client.post("/api/v1/devices", json={"device_id": "phone-4", "public_key": public_key()})
    response = await client.post("/api/v1/devices", json={"device_id": "phone-4", "public_key": public_key()})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "device_id_taken"


async def test_device_id_taken_by_another_user_is_a_conflict(
    client: AsyncClient, supervisor: User, contractor: User
) -> None:
    key = public_key()
    sign_in_as(supervisor)
    await client.post("/api/v1/devices", json={"device_id": "phone-5", "public_key": key})
    sign_in_as(contractor)
    response = await client.post("/api/v1/devices", json={"device_id": "phone-5", "public_key": key})
    assert response.status_code == 409


@pytest.mark.parametrize("bad_key", ["not base64!", base64.b64encode(b"junk").decode()])
async def test_invalid_public_key_is_422(client: AsyncClient, supervisor: User, bad_key: str) -> None:
    sign_in_as(supervisor)
    response = await client.post("/api/v1/devices", json={"device_id": "phone-6", "public_key": bad_key})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_public_key"


async def test_non_p256_key_is_refused(client: AsyncClient, supervisor: User) -> None:
    sign_in_as(supervisor)
    response = await client.post(
        "/api/v1/devices", json={"device_id": "phone-7", "public_key": public_key(ec.SECP384R1())}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_public_key"


async def test_device_id_with_pipe_is_refused(client: AsyncClient, supervisor: User) -> None:
    sign_in_as(supervisor)
    response = await client.post("/api/v1/devices", json={"device_id": "a|b", "public_key": public_key()})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_device"


# POST /devices/{id}/revoke


async def register(client: AsyncClient, user: User, device_id: str, key: str | None = None) -> dict[str, str]:
    sign_in_as(user)
    created = await client.post(
        "/api/v1/devices", json={"device_id": device_id, "public_key": key or public_key()}
    )
    assert created.status_code == 201
    return created.json()  # type: ignore[no-any-return]


async def test_ops_revokes_a_device(client: AsyncClient, supervisor: User, ops: User) -> None:
    device = await register(client, supervisor, "phone-8")
    sign_in_as(ops)
    response = await client.post(f"/api/v1/devices/{device['id']}/revoke")
    assert response.status_code == 200
    assert response.json()["revoked_at"] is not None


async def test_revoking_twice_keeps_the_first_time(client: AsyncClient, supervisor: User, ops: User) -> None:
    device = await register(client, supervisor, "phone-9")
    sign_in_as(ops)
    url = f"/api/v1/devices/{device['id']}/revoke"
    first = await client.post(url)
    second = await client.post(url)
    assert second.status_code == 200
    assert second.json()["revoked_at"] == first.json()["revoked_at"]


@pytest.mark.parametrize("role", ["supervisor", "contractor", "client"])
async def test_only_ops_can_revoke(
    client: AsyncClient, db_session: AsyncSession, supervisor: User, role: str
) -> None:
    device = await register(client, supervisor, f"phone-{role}")
    sign_in_as(await make_user(db_session, role))
    response = await client.post(f"/api/v1/devices/{device['id']}/revoke")
    assert response.status_code == 403


async def test_revoking_an_unknown_device_is_404(client: AsyncClient, ops: User) -> None:
    sign_in_as(ops)
    response = await client.post(f"/api/v1/devices/{uuid.uuid4()}/revoke")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "device_not_found"


async def test_a_revoked_device_cannot_be_registered_again(
    client: AsyncClient, supervisor: User, ops: User
) -> None:
    key = public_key()
    device = await register(client, supervisor, "phone-10", key)
    sign_in_as(ops)
    await client.post(f"/api/v1/devices/{device['id']}/revoke")
    sign_in_as(supervisor)
    response = await client.post("/api/v1/devices", json={"device_id": "phone-10", "public_key": key})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "device_revoked"


# service helper used by the Day 4 evidence checks


async def test_get_device_finds_by_device_id(db_session: AsyncSession, supervisor: User) -> None:
    device, created = await service.register_device(db_session, supervisor.id, "phone-11", public_key())
    assert created is True
    assert (await service.get_device(db_session, "phone-11")) == device
    assert await service.get_device(db_session, "missing") is None


async def test_service_rejects_a_bad_key(db_session: AsyncSession, supervisor: User) -> None:
    with pytest.raises(AppError) as err:
        await service.register_device(db_session, supervisor.id, "phone-12", "nope")
    assert err.value.code == "invalid_public_key"
