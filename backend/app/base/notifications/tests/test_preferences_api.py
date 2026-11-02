"""GET and PUT /me/notification-preferences: the two push settings in the design."""

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.base.users.models import User

URL = "/api/v1/me/notification-preferences"


async def make_user(session: AsyncSession, role: str = "supervisor") -> User:
    user = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role=role, status="active")
    session.add(user)
    await session.flush()
    return user


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {users.create_access_token(user)}"}


async def test_the_defaults_are_push_on_and_previews_shown(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    response = await client.get(URL, headers=auth(me))
    assert response.status_code == 200
    assert response.json() == {"push_enabled": True, "hide_previews": False}


async def test_saving_changes_what_is_read_back(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    saved = await client.put(URL, json={"push_enabled": False, "hide_previews": True}, headers=auth(me))
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"push_enabled": False, "hide_previews": True}
    assert (await client.get(URL, headers=auth(me))).json() == {"push_enabled": False, "hide_previews": True}


async def test_saving_the_same_values_twice_is_fine(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    body = {"push_enabled": False, "hide_previews": False}
    first = await client.put(URL, json=body, headers=auth(me))
    second = await client.put(URL, json=body, headers=auth(me))
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()


async def test_the_idempotency_key_replays_the_answer(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    headers = auth(me) | {"Idempotency-Key": "prefs-1"}
    body = {"push_enabled": True, "hide_previews": True}
    first = await client.put(URL, json=body, headers=headers)
    second = await client.put(URL, json=body, headers=headers)
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()


async def test_one_persons_settings_never_touch_another(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    other = await make_user(db_session, "contractor")
    await client.put(URL, json={"push_enabled": False, "hide_previews": True}, headers=auth(me))
    assert (await client.get(URL, headers=auth(other))).json() == {
        "push_enabled": True,
        "hide_previews": False,
    }


@pytest.mark.parametrize(
    "body",
    [
        {"push_enabled": True},  # both are required: a PUT replaces them
        {"hide_previews": True},
        {"push_enabled": "yes", "hide_previews": False},  # a real boolean, not a string
        {"push_enabled": 1, "hide_previews": 0},
        {},
    ],
)
async def test_a_bad_body_is_422(
    client: AsyncClient, db_session: AsyncSession, body: dict[str, object]
) -> None:
    me = await make_user(db_session)
    assert (await client.put(URL, json=body, headers=auth(me))).status_code == 422


async def test_spot_check_sms_is_not_a_setting(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    body = {"push_enabled": False, "hide_previews": False, "spot_check_sms": False}
    response = await client.put(URL, json=body, headers=auth(me))
    assert response.status_code == 200
    assert "spot_check_sms" not in response.json()


@pytest.mark.parametrize("role", ["client", "contractor", "supervisor", "supplier", "ops"])
async def test_every_role_can_read_its_settings(
    client: AsyncClient, db_session: AsyncSession, role: str
) -> None:
    me = await make_user(db_session, role)
    assert (await client.get(URL, headers=auth(me))).status_code == 200


async def test_signed_out_is_401(client: AsyncClient) -> None:
    assert (await client.get(URL)).status_code == 401
    assert (await client.put(URL, json={"push_enabled": True, "hide_previews": False})).status_code == 401
