"""notify() and notify_address(): channel order, fallback, what is saved, and templates."""

import secrets
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications import LOGIN_CODE, Template, notify, notify_address
from app.base.notifications.adapters import FakeAdapter
from app.base.notifications.models import Channel, Notification
from app.base.users.models import User
from app.core.errors import AppError

CLAIMED = Template(
    name="milestone.claimed",
    title="Milestone claimed",
    text="{contractor} says '{milestone}' is done. Your supervisor will check it next.",
)
DATA = {"contractor": "Obi Builders", "milestone": "Foundation"}


async def make_user(session: AsyncSession, *, email: str | None = "ada@example.com") -> User:
    user = User(
        phone=f"+234803{secrets.randbelow(10**7):07d}",
        email=email and f"{secrets.token_hex(4)}.{email}",
        role="client",
        status="active",
    )
    session.add(user)
    await session.flush()
    return user


def fakes(**failing: bool) -> dict[Channel, FakeAdapter]:
    return {channel: FakeAdapter(fail=failing.get(channel.value, False)) for channel in Channel}


async def saved(session: AsyncSession, user_id: uuid.UUID | None) -> list[Notification]:
    rows = await session.scalars(select(Notification).where(Notification.user_id == user_id))
    return list(rows)


# --- notify(): order and fallback --------------------------------------------------------------


async def test_whatsapp_first_by_default(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    adapters = fakes()
    row = await notify(db_session, user.id, CLAIMED, DATA, adapters=adapters)

    assert (row.channel, row.status, row.recipient) == ("whatsapp", "sent", user.phone)
    assert row.provider_ref == "fake-1"
    assert row.attempts == 1 and row.error is None and row.sent_at is not None
    [(to, message)] = adapters[Channel.WHATSAPP].sent
    assert to == user.phone
    assert message.text == "Obi Builders says 'Foundation' is done. Your supervisor will check it next."
    assert adapters[Channel.SMS].sent == []  # stops at the first channel that works


async def test_first_channel_fails_so_the_next_one_is_used(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    adapters = fakes(whatsapp=True)
    row = await notify(db_session, user.id, CLAIMED, DATA, adapters=adapters)

    # WhatsApp fails, push has no address (no device token), SMS delivers.
    assert (row.channel, row.status) == ("sms", "sent")
    assert row.attempts == 3
    assert row.error is not None
    assert "whatsapp: fake provider is down" in row.error
    assert "push: no address" in row.error
    assert len(adapters[Channel.SMS].sent) == 1


async def test_unconfigured_channels_are_skipped(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    email = FakeAdapter()
    row = await notify(db_session, user.id, CLAIMED, DATA, adapters={Channel.EMAIL: email})
    assert (row.channel, row.recipient) == ("email", user.email)
    assert row.error == "whatsapp: not configured; push: no address; sms: not configured"


async def test_channels_argument_sets_the_order(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    adapters = fakes()
    row = await notify(db_session, user.id, CLAIMED, DATA, ["email", "sms", "email"], adapters=adapters)
    assert row.channel == "email"
    assert adapters[Channel.WHATSAPP].sent == []


async def test_user_without_email_falls_through_to_failed(db_session: AsyncSession) -> None:
    user = await make_user(db_session, email=None)
    row = await notify(db_session, user.id, CLAIMED, DATA, ["email"], adapters=fakes())
    assert (row.status, row.error, row.recipient) == ("failed", "email: no address", None)


async def test_every_channel_failing_saves_a_failed_row(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    adapters = fakes(whatsapp=True, sms=True, email=True)
    row = await notify(db_session, user.id, CLAIMED, DATA, adapters=adapters)

    assert row.status == "failed"
    assert row.channel == "email"  # the last one tried
    assert row.attempts == 4
    assert row.sent_at is None and row.provider_ref is None
    assert [r.id for r in await saved(db_session, user.id)] == [row.id]


async def test_payload_is_saved_json_safe(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    milestone_id = uuid.uuid4()
    template = Template(name="t", text="{milestone}")
    row = await notify(
        db_session, user.id, template, {"milestone": "Roof", "id": milestone_id}, adapters=fakes()
    )
    assert row.payload == {"milestone": "Roof", "id": str(milestone_id)}
    assert row.template == "t"


async def test_unknown_user_is_404(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await notify(db_session, uuid.uuid4(), CLAIMED, DATA, adapters=fakes())
    assert (error.value.status_code, error.value.code) == (404, "user_not_found")


async def test_missing_template_data_is_refused_before_sending(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    adapters = fakes()
    with pytest.raises(ValueError, match="contractor"):
        await notify(db_session, user.id, CLAIMED, {"milestone": "Foundation"}, adapters=adapters)
    assert all(a.sent == [] for a in adapters.values())
    assert await saved(db_session, user.id) == []


@pytest.mark.parametrize("channels", [["pigeon"], []])
async def test_bad_channel_lists_are_refused(db_session: AsyncSession, channels: list[str]) -> None:
    user = await make_user(db_session)
    with pytest.raises(ValueError):
        await notify(db_session, user.id, CLAIMED, DATA, channels, adapters=fakes())


# --- notify_address(): login codes -------------------------------------------------------------


async def test_login_code_to_an_address_without_a_user(db_session: AsyncSession) -> None:
    sms = FakeAdapter()
    row = await notify_address(
        db_session, "+2348031234567", "sms", LOGIN_CODE, {"code": "482913"}, adapters={Channel.SMS: sms}
    )
    [(to, message)] = sms.sent
    assert to == "+2348031234567"
    assert "482913" in message.text
    assert (row.user_id, row.channel, row.status, row.recipient) == (None, "sms", "sent", "+2348031234567")
    assert row.payload == {}  # the code is never stored
    assert row.template == "auth.login_code"


async def test_login_code_channel_not_configured_is_503(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await notify_address(db_session, "ada@example.com", "email", LOGIN_CODE, {"code": "1"}, adapters={})
    assert (error.value.status_code, error.value.code) == (503, "notifications_not_configured")


async def test_login_code_provider_failure_is_502_and_saves_nothing(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await notify_address(
            db_session,
            "+2348031234567",
            "sms",
            LOGIN_CODE,
            {"code": "1"},
            adapters={Channel.SMS: FakeAdapter(fail=True)},
        )
    assert (error.value.status_code, error.value.code) == (502, "notification_failed")
    assert await saved(db_session, None) == []


# --- templates ---------------------------------------------------------------------------------


def test_template_renders_title_and_subject() -> None:
    message = CLAIMED.render(DATA)
    assert (message.template, message.title, message.subject) == (
        "milestone.claimed",
        "Milestone claimed",
        "Milestone claimed",
    )
    assert Template(name="t", text="x", subject="Hello").render({}).subject == "Hello"


def test_template_ignores_extra_data() -> None:
    assert Template(name="t", text="Hi {name}").render({"name": "Ada", "extra": 1}).text == "Hi Ada"


@pytest.mark.parametrize("text", ["{user.name}", "{0}", "{items[0]}"])
def test_template_allows_plain_names_only(text: str) -> None:
    with pytest.raises(ValueError, match="plain"):
        Template(name="t", text=text)
