"""The spot-check message: queued after commit, to the visiting supervisor only, push then SMS, sent once."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications.adapters import FakeAdapter
from app.base.notifications.models import Channel
from app.base.notifications.service import save_push_token
from app.base.users.models import User
from app.features.projects.models import Project
from app.features.supervision import notices, rotation
from app.features.supervision.models import SpotCheck
from app.features.supervision.tests.factories import make_vetted

TOMORROW = datetime.now(UTC) + timedelta(days=1)


def fakes() -> dict[Channel, FakeAdapter]:
    return {channel: FakeAdapter() for channel in Channel}


async def scheduled(db_session: AsyncSession, project: Project, who: User, ops: User) -> SpotCheck:
    return await rotation.schedule_project_spot_check(db_session, project.id, who.id, TOMORROW, ops.id)


async def test_scheduling_queues_the_message_for_after_commit(
    db_session: AsyncSession, project: Project, vetted: User, ops: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    queued: list[uuid.UUID] = []
    monkeypatch.setattr(notices, "enqueue", queued.append)
    spot_check = await scheduled(db_session, project, vetted, ops)
    assert queued == []  # nothing yet: the transaction has not committed
    await db_session.commit()
    assert queued == [spot_check.id]


async def test_a_rolled_back_schedule_tells_nobody(
    db_session: AsyncSession, project: Project, vetted: User, ops: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    queued: list[uuid.UUID] = []
    monkeypatch.setattr(notices, "enqueue", queued.append)
    await scheduled(db_session, project, vetted, ops)
    await db_session.rollback()
    assert queued == []


async def test_push_and_sms_when_the_phone_has_push(
    db_session: AsyncSession, project: Project, vetted: User, ops: User
) -> None:
    await save_push_token(db_session, vetted.id, uuid.uuid4(), "token-aaaaaaaaaaaaaaaaaaaa")
    vetted.role = "supervisor"
    spot_check = await scheduled(db_session, project, vetted, ops)
    adapters = fakes()
    rows = await notices.send_assigned(db_session, spot_check.id, adapters=adapters)
    assert [r.channel for r in rows] == ["push", "sms"]
    ((to, push),) = adapters[Channel.PUSH].sent
    assert to == "token-aaaaaaaaaaaaaaaaaaaa"
    assert dict(push.link) == {"project_id": str(project.id), "spot_check_id": str(spot_check.id)}
    ((sms_to, sms),) = adapters[Channel.SMS].sent
    assert sms_to == vetted.phone
    assert project.title in sms.text
    assert "Nigerian time" in sms.text


async def test_no_push_means_one_sms_not_two(
    db_session: AsyncSession, project: Project, vetted: User, ops: User
) -> None:
    spot_check = await scheduled(db_session, project, vetted, ops)
    adapters = fakes()
    rows = await notices.send_assigned(db_session, spot_check.id, adapters=adapters)
    assert [r.channel for r in rows] == ["sms"]
    assert len(adapters[Channel.SMS].sent) == 1
    assert adapters[Channel.PUSH].sent == []


async def test_running_twice_sends_nothing_new(
    db_session: AsyncSession, project: Project, vetted: User, ops: User
) -> None:
    await save_push_token(db_session, vetted.id, uuid.uuid4(), "token-bbbbbbbbbbbbbbbbbbbb")
    spot_check = await scheduled(db_session, project, vetted, ops)
    adapters = fakes()
    await notices.send_assigned(db_session, spot_check.id, adapters=adapters)
    await notices.send_assigned(db_session, spot_check.id, adapters=adapters)
    assert len(adapters[Channel.PUSH].sent) == 1
    assert len(adapters[Channel.SMS].sent) == 1


async def test_only_the_visiting_supervisor_hears(
    db_session: AsyncSession, project: Project, vetted: User, ops: User
) -> None:
    other = await make_vetted(db_session, ops)
    spot_check = await scheduled(db_session, project, other, ops)
    adapters = fakes()
    await notices.send_assigned(db_session, spot_check.id, adapters=adapters)
    recipients = {to for a in adapters.values() for to, _ in a.sent}
    assert recipients == {other.phone}


async def test_a_finished_or_missing_spot_check_sends_nothing(
    db_session: AsyncSession, project: Project, vetted: User, ops: User
) -> None:
    adapters = fakes()
    assert await notices.send_assigned(db_session, uuid.uuid4(), adapters=adapters) == []
    spot_check = await scheduled(db_session, project, vetted, ops)
    spot_check.completed_at = datetime.now(UTC)
    await db_session.flush()
    assert await notices.send_assigned(db_session, spot_check.id, adapters=adapters) == []
    assert all(a.sent == [] for a in adapters.values())
