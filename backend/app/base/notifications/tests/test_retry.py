"""notify() keys (send once) and retry_failed(): failed messages are sent again, within limits."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications import Template, notify
from app.base.notifications.adapters import FakeAdapter
from app.base.notifications.models import Channel, Notification
from app.base.notifications.service import retry_failed
from app.base.notifications.tests.test_notify import fakes, make_user

ROOF = Template(name="test.retry.roof", text="'{milestone}' is done.")
DATA = {"milestone": "Roof"}


# --- keys --------------------------------------------------------------------------------------


async def test_same_key_sends_once(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    adapters = fakes()
    first = await notify(db_session, user.id, ROOF, DATA, key="claimed:m1", adapters=adapters)
    again = await notify(db_session, user.id, ROOF, DATA, key="claimed:m1", adapters=adapters)

    assert again.id == first.id
    assert len(adapters[Channel.WHATSAPP].sent) == 1
    assert first.payload == {"milestone": "Roof", "_key": "claimed:m1"}


async def test_different_keys_both_send(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    adapters = fakes()
    await notify(db_session, user.id, ROOF, DATA, key="a", adapters=adapters)
    await notify(db_session, user.id, ROOF, DATA, key="b", adapters=adapters)
    await notify(db_session, user.id, ROOF, DATA, adapters=adapters)  # no key: always sends
    assert len(adapters[Channel.WHATSAPP].sent) == 3


# --- retry_failed ------------------------------------------------------------------------------


async def failed_row(db_session: AsyncSession) -> Notification:
    user = await make_user(db_session)
    row = await notify(db_session, user.id, ROOF, DATA, adapters={})  # nothing configured
    assert row.status == "failed"
    return row


async def test_failed_row_is_sent_once_a_channel_works(db_session: AsyncSession) -> None:
    row = await failed_row(db_session)
    sms = FakeAdapter()

    counts = await retry_failed(db_session, adapters={Channel.SMS: sms})

    assert counts["sent"] >= 1
    await db_session.refresh(row)
    assert (row.status, row.channel) == ("sent", "sms")
    assert row.sent_at is not None and row.provider_ref == "fake-1"
    assert row.attempts == 4 + 3  # 4 in the first round, then WhatsApp, push, SMS
    assert sms.sent[0][1].text == "'Roof' is done."


async def test_still_failing_counts_the_attempts(db_session: AsyncSession) -> None:
    row = await failed_row(db_session)
    await retry_failed(db_session, adapters=fakes(whatsapp=True, sms=True, email=True))
    await db_session.refresh(row)
    assert row.status == "failed"
    assert row.attempts == 8
    assert "whatsapp: fake provider is down" in (row.error or "")


async def test_old_or_exhausted_rows_are_left_alone(db_session: AsyncSession) -> None:
    old = await failed_row(db_session)
    old.created_at = datetime.now(UTC) - timedelta(hours=25)
    exhausted = await failed_row(db_session)
    exhausted.attempts = 20
    await db_session.flush()

    await retry_failed(db_session, adapters={Channel.SMS: FakeAdapter()})

    await db_session.refresh(old)
    await db_session.refresh(exhausted)
    assert (old.status, old.attempts) == ("failed", 4)
    assert (exhausted.status, exhausted.attempts) == ("failed", 20)


async def test_unknown_template_is_skipped(db_session: AsyncSession) -> None:
    row = await failed_row(db_session)
    row.template = "test.retry.not-registered"
    await db_session.flush()
    await retry_failed(db_session, adapters={Channel.SMS: FakeAdapter()})
    await db_session.refresh(row)
    assert row.status == "failed"
