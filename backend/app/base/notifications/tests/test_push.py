"""Push delivery: who it reaches, the settings that stop it or hide its words, and dead tokens."""

import json
import secrets
import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications import Template, notify
from app.base.notifications.adapters import FakeAdapter, FcmPushAdapter, SendError, TokenGone
from app.base.notifications.models import Channel, PushToken
from app.base.notifications.service import (
    HIDDEN_TEXT,
    HIDDEN_TITLE,
    Preferences,
    forget_push_token,
    get_preferences,
    save_push_token,
    set_preferences,
)
from app.base.notifications.settings import NotificationSettings
from app.base.notifications.templates import Rendered
from app.base.users.models import User

CLAIMED = Template(
    name="test.push_claimed",
    title="Milestone claimed",
    text="{contractor} says '{milestone}' is done. It is worth {amount}.",
)
DATA = {
    "contractor": "Obi Builders",
    "milestone": "Foundation",
    "amount": "₦2,000,000",
    "project_id": "11111111-1111-1111-1111-111111111111",
    "milestone_id": "22222222-2222-2222-2222-222222222222",
}


async def make_user(session: AsyncSession, role: str = "supervisor") -> User:
    user = User(
        phone=f"+234803{secrets.randbelow(10**7):07d}",
        email=f"{secrets.token_hex(4)}@example.com",
        role=role,
        status="active",
    )
    session.add(user)
    await session.flush()
    return user


class GoneAdapter:
    """A push provider that says every token is dead."""

    async def send(self, to: str, message: Rendered) -> str:
        raise TokenGone("push: the device token is no longer registered")


def fakes(**over: Any) -> dict[Channel, Any]:
    adapters: dict[Channel, Any] = {c: FakeAdapter() for c in Channel}
    adapters.update({Channel(k): v for k, v in over.items()})
    return adapters


async def tokens_of(session: AsyncSession, user: User) -> list[str]:
    rows = await session.scalars(
        select(PushToken).where(PushToken.user_id == user.id).order_by(PushToken.token)
    )
    return [r.token for r in rows]


# --- who push reaches --------------------------------------------------------------------------


async def test_push_reaches_a_supervisors_registered_phone(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-aaaaaaaaaaaaaaaaaaaa")
    adapters = fakes()
    row = await notify(db_session, user.id, CLAIMED, DATA, ("push", "sms"), adapters=adapters)
    assert row.channel == "push"
    assert row.status == "sent"
    assert row.recipient == "1 phone"  # never the token itself
    assert [t for t, _ in adapters[Channel.PUSH].sent] == ["token-aaaaaaaaaaaaaaaaaaaa"]
    assert adapters[Channel.SMS].sent == []


async def test_push_carries_the_ids_that_open_the_right_screen(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "contractor")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-bbbbbbbbbbbbbbbbbbbb")
    adapters = fakes()
    await notify(db_session, user.id, CLAIMED, DATA, ("push",), adapters=adapters)
    _, message = adapters[Channel.PUSH].sent[0]
    assert dict(message.link) == {"project_id": DATA["project_id"], "milestone_id": DATA["milestone_id"]}


async def test_the_link_holds_only_ids_never_names_or_amounts(db_session: AsyncSession) -> None:
    message = CLAIMED.render(DATA)
    assert {k for k, _ in message.link} == {"project_id", "milestone_id"}
    assert "Obi" not in str(message.link)
    assert "₦" not in str(message.link)
    assert CLAIMED.render({**DATA, "project_id": "", "milestone_id": None}).link == ()


@pytest.mark.parametrize("role", ["client", "supplier", "ops"])
async def test_push_is_only_for_the_app_roles(db_session: AsyncSession, role: str) -> None:
    user = await make_user(db_session, role)
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-cccccccccccccccccccc")
    adapters = fakes()
    row = await notify(db_session, user.id, CLAIMED, DATA, ("push", "sms"), adapters=adapters)
    assert row.channel == "sms"  # skipped push, used the next channel
    assert adapters[Channel.PUSH].sent == []


async def test_no_registered_phone_falls_back(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    adapters = fakes()
    row = await notify(db_session, user.id, CLAIMED, DATA, ("push", "sms"), adapters=adapters)
    assert row.channel == "sms"
    assert "push: no address" in (row.error or "")


async def test_every_registered_phone_gets_it(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-phone-one-aaaaaaaa")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-phone-two-bbbbbbbb")
    adapters = fakes()
    row = await notify(db_session, user.id, CLAIMED, DATA, ("push",), adapters=adapters)
    assert row.recipient == "2 phones"
    assert sorted(t for t, _ in adapters[Channel.PUSH].sent) == [
        "token-phone-one-aaaaaaaa",
        "token-phone-two-bbbbbbbb",
    ]


async def test_push_without_an_adapter_is_not_configured(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-dddddddddddddddddddd")
    adapters = fakes()
    del adapters[Channel.PUSH]
    row = await notify(db_session, user.id, CLAIMED, DATA, ("push", "sms"), adapters=adapters)
    assert row.channel == "sms"
    assert "push: not configured" in (row.error or "")


# --- the person's settings ---------------------------------------------------------------------


async def test_push_switched_off_falls_back_and_keeps_the_token(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-eeeeeeeeeeeeeeeeeeee")
    await set_preferences(db_session, user.id, push_enabled=False, hide_previews=False)
    adapters = fakes()
    row = await notify(db_session, user.id, CLAIMED, DATA, ("push", "sms"), adapters=adapters)
    assert row.channel == "sms"
    assert "push: turned off" in (row.error or "")
    assert adapters[Channel.PUSH].sent == []
    assert await tokens_of(db_session, user) == ["token-eeeeeeeeeeeeeeeeeeee"]


async def test_hidden_previews_send_only_the_generic_line(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-ffffffffffffffffffff")
    await set_preferences(db_session, user.id, push_enabled=True, hide_previews=True)
    adapters = fakes()
    await notify(db_session, user.id, CLAIMED, DATA, ("push",), adapters=adapters)
    _, message = adapters[Channel.PUSH].sent[0]
    assert (message.title, message.text) == (HIDDEN_TITLE, HIDDEN_TEXT)
    assert "Obi" not in message.text
    assert "₦" not in message.text
    assert dict(message.link)["milestone_id"] == DATA["milestone_id"]  # it still opens the right screen


async def test_hiding_previews_does_not_change_other_channels(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    await set_preferences(db_session, user.id, push_enabled=True, hide_previews=True)
    adapters = fakes()
    await notify(db_session, user.id, CLAIMED, DATA, ("sms",), adapters=adapters)
    _, message = adapters[Channel.SMS].sent[0]
    assert "Obi Builders" in message.text


async def test_preferences_default_to_push_on_and_previews_shown(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    assert await get_preferences(db_session, user.id) == Preferences(push_enabled=True, hide_previews=False)


async def test_saving_the_same_preferences_twice_changes_nothing(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    first = await set_preferences(db_session, user.id, push_enabled=False, hide_previews=True)
    second = await set_preferences(db_session, user.id, push_enabled=False, hide_previews=True)
    assert first == second == Preferences(push_enabled=False, hide_previews=True)
    assert await get_preferences(db_session, user.id) == first


# --- tokens ------------------------------------------------------------------------------------


async def test_a_dead_token_is_forgotten_and_the_next_channel_runs(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-gone-aaaaaaaaaaaaa")
    adapters = fakes(push=GoneAdapter())
    row = await notify(db_session, user.id, CLAIMED, DATA, ("push", "sms"), adapters=adapters)
    assert row.channel == "sms"
    assert await tokens_of(db_session, user) == []


async def test_a_provider_outage_keeps_the_token(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-keep-aaaaaaaaaaaaa")
    adapters = fakes(push=FakeAdapter(fail=True))
    row = await notify(db_session, user.id, CLAIMED, DATA, ("push", "sms"), adapters=adapters)
    assert row.channel == "sms"
    assert await tokens_of(db_session, user) == ["token-keep-aaaaaaaaaaaaa"]


async def test_one_dead_phone_does_not_stop_the_live_one(db_session: AsyncSession) -> None:
    user = await make_user(db_session, "supervisor")
    live, dead = FakeAdapter(), GoneAdapter()

    class Mixed:
        async def send(self, to: str, message: Rendered) -> str:
            return await (dead if "dead" in to else live).send(to, message)

    await save_push_token(db_session, user.id, uuid.uuid4(), "token-dead-aaaaaaaaaaaaaa")
    await save_push_token(db_session, user.id, uuid.uuid4(), "token-live-aaaaaaaaaaaaaa")
    row = await notify(db_session, user.id, CLAIMED, DATA, ("push",), adapters=fakes(push=Mixed()))
    assert row.channel == "push"
    assert row.recipient == "1 phone"
    assert await tokens_of(db_session, user) == ["token-live-aaaaaaaaaaaaaa"]


async def test_a_new_token_for_the_same_device_replaces_the_old_one(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    device = uuid.uuid4()
    await save_push_token(db_session, user.id, device, "token-old-aaaaaaaaaaaaaaaaa")
    await save_push_token(db_session, user.id, device, "token-new-aaaaaaaaaaaaaaaaa")
    assert await tokens_of(db_session, user) == ["token-new-aaaaaaaaaaaaaaaaa"]


async def test_a_token_that_moves_to_another_phone_leaves_the_first(db_session: AsyncSession) -> None:
    first = await make_user(db_session, "supervisor")
    second = await make_user(db_session, "contractor")
    await save_push_token(db_session, first.id, uuid.uuid4(), "token-shared-aaaaaaaaaaaa")
    await save_push_token(db_session, second.id, uuid.uuid4(), "token-shared-aaaaaaaaaaaa")
    assert await tokens_of(db_session, first) == []  # one phone is never reachable as two people
    assert await tokens_of(db_session, second) == ["token-shared-aaaaaaaaaaaa"]


async def test_forgetting_a_token_is_quiet_when_there_is_none(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    device = uuid.uuid4()
    await save_push_token(db_session, user.id, device, "token-bye-aaaaaaaaaaaaaaaaa")
    await forget_push_token(db_session, device)
    await forget_push_token(db_session, device)
    assert await tokens_of(db_session, user) == []


# --- the Firebase adapter ----------------------------------------------------------------------


def fcm_adapter(handler: Any) -> FcmPushAdapter:
    import jwt as _jwt  # noqa: F401  (the adapter signs with the service account)
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    account = {"client_email": "push@x.iam.gserviceaccount.com", "private_key": pem}
    settings = NotificationSettings(  # type: ignore[call-arg]
        _env_file=None, fcm_project_id="p", fcm_service_account_json=json.dumps(account)
    )
    return FcmPushAdapter(settings, transport=httpx.MockTransport(handler))


def fcm_handler(answer: httpx.Response, seen: list[dict[str, Any]] | None = None) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth2" in str(request.url):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        if seen is not None:
            seen.append(json.loads(request.content)["message"])
        return answer

    return handler


async def test_fcm_sends_the_template_and_the_ids_as_string_data() -> None:
    seen: list[dict[str, Any]] = []
    adapter = fcm_adapter(fcm_handler(httpx.Response(200, json={"name": "m/1"}), seen))
    await adapter.send("tok", CLAIMED.render(DATA))
    assert seen[0]["data"] == {
        "template": "test.push_claimed",
        "project_id": DATA["project_id"],
        "milestone_id": DATA["milestone_id"],
    }
    assert all(isinstance(v, str) for v in seen[0]["data"].values())


async def test_fcm_unregistered_is_a_dead_token() -> None:
    body = {
        "error": {
            "code": 404,
            "status": "NOT_FOUND",
            "details": [
                {"@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError", "errorCode": "UNREGISTERED"}
            ],
        }
    }
    adapter = fcm_adapter(fcm_handler(httpx.Response(404, json=body)))
    with pytest.raises(TokenGone):
        await adapter.send("old", CLAIMED.render(DATA))


@pytest.mark.parametrize("code", [400, 401, 403, 429, 500, 503])
async def test_other_fcm_failures_never_delete_a_token(code: int) -> None:
    adapter = fcm_adapter(fcm_handler(httpx.Response(code, json={"error": {"status": "INVALID_ARGUMENT"}})))
    with pytest.raises(SendError) as err:
        await adapter.send("tok", CLAIMED.render(DATA))
    assert not isinstance(err.value, TokenGone)
