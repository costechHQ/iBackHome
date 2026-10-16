"""Milestone messages: queued only after commit, who hears what, sent once, and daily reminders."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications.adapters import FakeAdapter
from app.base.notifications.models import Channel, Notification
from app.base.users.models import User
from app.features.milestones import notices, service
from app.features.milestones.models import MilestoneStatus, Verification
from app.features.milestones.tests.factories import Site, active_project, bearer, set_project_status
from app.features.projects import service as projects

S = MilestoneStatus

Queued = list[tuple[uuid.UUID, str, str]]


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> Queued:
    """What would be queued for Celery, instead of queuing it."""
    seen: Queued = []
    monkeypatch.setattr(notices, "enqueue_update", lambda m, e, k: seen.append((m, e, k)))
    return seen


def fakes() -> dict[Channel, FakeAdapter]:
    return {channel: FakeAdapter() for channel in Channel}


def sent_to(adapters: dict[Channel, FakeAdapter], user: User) -> list[tuple[Channel, str]]:
    """(channel, text) of every message that reached this user."""
    found = []
    for channel, adapter in adapters.items():
        for to, message in adapter.sent:
            if to in (user.phone, user.email):
                found.append((channel, message.text))
    return found


async def give_email(session: AsyncSession, user: User) -> None:
    user.email = f"{secrets.token_hex(4)}@example.com"
    await session.flush()


# --- which moves send a message -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("before", "after", "event"),
    [
        (S.FUNDED, S.CLAIMED, "claimed"),
        (S.CLAIMED, S.VERIFIED, "verified"),
        (S.CLAIMED, S.FUNDED, "rejected"),
        (S.APPROVED, S.RELEASED, "released"),
        (S.DISPUTED, S.RELEASED, "released"),
        (S.PENDING, S.FUNDED, None),
        (S.VERIFIED, S.APPROVED, None),
        (S.VERIFIED, S.DISPUTED, None),
        (S.DISPUTED, S.FUNDED, None),
    ],
)
def test_event_for_each_move(before: MilestoneStatus, after: MilestoneStatus, event: str | None) -> None:
    assert notices.event_for(before, after) == event


def test_amounts_are_formatted_without_floats() -> None:
    assert notices.format_amount(8_000_000_00, "NGN") == "NGN 8,000,000.00"
    assert notices.format_amount(1_005, "GBP") == "GBP 10.05"
    assert notices.format_amount(7, "USD") == "USD 0.07"


# --- queued only after commit -------------------------------------------------------------------


async def test_claim_queues_the_message_after_commit(db_session: AsyncSession, queued: Queued) -> None:
    site = await active_project(db_session, first_status=S.FUNDED)
    milestone = site.milestones[0]
    await service.claim(db_session, milestone.id, site.contractor)  # type: ignore[arg-type]
    assert queued == []  # nothing before the commit

    await db_session.commit()
    [(milestone_id, event, key)] = queued
    assert (milestone_id, event) == (milestone.id, "claimed")
    assert key.startswith(f"claimed:{milestone.id}:")


async def test_rolled_back_claim_queues_nothing(db_session: AsyncSession, queued: Queued) -> None:
    site = await active_project(db_session, first_status=S.FUNDED)
    await service.claim(db_session, site.milestones[0].id, site.contractor)  # type: ignore[arg-type]
    await db_session.rollback()
    assert queued == []
    await db_session.commit()  # a later commit doesn't bring the dropped message back
    assert queued == []


async def test_claim_route_queues_the_client_message(
    client: AsyncClient, db_session: AsyncSession, queued: Queued
) -> None:
    """Backend Day 5 "done when": claiming a milestone sends the client a message."""
    site = await active_project(db_session, first_status=S.FUNDED)
    milestone = site.milestones[0]
    response = await client.post(f"/api/v1/milestones/{milestone.id}/claim", headers=bearer(site.contractor))
    assert response.status_code == 200
    assert [(m, e) for m, e, _ in queued] == [(milestone.id, "claimed")]

    adapters = fakes()
    await notices.send_update(db_session, milestone.id, "claimed", queued[0][2], adapters=adapters)
    [(channel, text)] = sent_to(adapters, site.client)
    assert channel == Channel.WHATSAPP
    assert "'Foundation' on 4-bedroom bungalow is done" in text


async def test_moves_without_a_message_queue_nothing(db_session: AsyncSession, queued: Queued) -> None:
    site = await active_project(db_session, first_status=S.PENDING)
    await service.mark_funded(db_session, site.milestones[0].id)
    await db_session.commit()
    assert queued == []


# --- who hears what -----------------------------------------------------------------------------


async def claimed_site(db_session: AsyncSession) -> Site:
    site = await active_project(db_session, first_status=S.FUNDED)
    site.contractor.full_name = "Obi Builders"
    await db_session.flush()
    return site


async def test_claimed_tells_client_and_supervisor(db_session: AsyncSession) -> None:
    site = await claimed_site(db_session)
    adapters = fakes()
    rows = await notices.send_update(db_session, site.milestones[0].id, "claimed", "k1", adapters=adapters)

    assert len(rows) == 2
    assert sent_to(adapters, site.client) == [
        (
            Channel.WHATSAPP,
            "Obi Builders says 'Foundation' on 4-bedroom bungalow is done. "
            "Your supervisor will check it on site next.",
        )
    ]
    # Push first for the supervisor; no push token yet, so it falls back to WhatsApp.
    [(channel, text)] = sent_to(adapters, site.supervisor)
    assert channel == Channel.WHATSAPP
    assert text == "'Foundation' on 4-bedroom bungalow has been claimed. Please visit the site and verify it."
    assert sent_to(adapters, site.contractor) == []


async def test_running_twice_sends_nothing_new(db_session: AsyncSession) -> None:
    site = await claimed_site(db_session)
    adapters = fakes()
    first = await notices.send_update(db_session, site.milestones[0].id, "claimed", "k2", adapters=adapters)
    again = await notices.send_update(db_session, site.milestones[0].id, "claimed", "k2", adapters=adapters)
    assert [r.id for r in again] == [r.id for r in first]
    assert sum(len(a.sent) for a in adapters.values()) == 2


async def test_no_supervisor_yet_skips_them(db_session: AsyncSession) -> None:
    site = await claimed_site(db_session)
    project = await projects.get_project(db_session, site.project_id)
    project.supervisor_id = None
    await db_session.flush()
    rows = await notices.send_update(db_session, site.milestones[0].id, "claimed", "k3", adapters=fakes())
    assert [r.user_id for r in rows] == [site.client.id]


async def test_verified_tells_client_on_whatsapp_and_email_and_the_contractor(
    db_session: AsyncSession,
) -> None:
    site = await claimed_site(db_session)
    await give_email(db_session, site.client)
    adapters = fakes()
    await notices.send_update(db_session, site.milestones[0].id, "verified", "k4", adapters=adapters)

    client_got = sent_to(adapters, site.client)
    assert [c for c, _ in client_got] == [Channel.WHATSAPP, Channel.EMAIL]
    assert "approve it to release NGN 8,000,000.00 to your contractor" in client_got[0][1]
    [(_, text)] = sent_to(adapters, site.contractor)
    assert text == (
        "'Foundation' on 4-bedroom bungalow was verified by the supervisor. The client approves it next."
    )


async def test_client_without_email_gets_one_message(db_session: AsyncSession) -> None:
    site = await claimed_site(db_session)
    adapters = fakes()
    rows = await notices.send_update(db_session, site.milestones[0].id, "verified", "k5", adapters=adapters)
    assert [c for c, _ in sent_to(adapters, site.client)] == [Channel.WHATSAPP]
    assert len(rows) == 2  # client once, contractor once


async def test_no_second_email_when_whatsapp_already_fell_back_to_email(db_session: AsyncSession) -> None:
    site = await claimed_site(db_session)
    await give_email(db_session, site.client)
    adapters = {Channel.EMAIL: FakeAdapter()}  # only email works
    await notices.send_update(db_session, site.milestones[0].id, "released", "k6", adapters=adapters)
    assert [c for c, _ in sent_to(adapters, site.client)] == [Channel.EMAIL]


async def test_rejected_tells_the_contractor_why(db_session: AsyncSession) -> None:
    site = await claimed_site(db_session)
    milestone = site.milestones[0]
    db_session.add(
        Verification(
            milestone_id=milestone.id,
            supervisor_id=site.supervisor.id,
            checklist=[],
            notes="Blockwork not plumb on the east wall.",
            decision="rejected",
        )
    )
    await db_session.flush()
    adapters = fakes()
    await notices.send_update(db_session, milestone.id, "rejected", "k7", adapters=adapters)

    [(_, text)] = sent_to(adapters, site.contractor)
    assert text == (
        "'Foundation' on 4-bedroom bungalow was not verified: Blockwork not plumb on the east wall. "
        "Fix the work and claim it again."
    )
    assert sent_to(adapters, site.client) == []


async def test_released_tells_client_and_contractor_the_amount(db_session: AsyncSession) -> None:
    site = await claimed_site(db_session)
    adapters = fakes()
    await notices.send_update(db_session, site.milestones[0].id, "released", "k8", adapters=adapters)
    [(_, to_client)] = sent_to(adapters, site.client)
    [(_, to_contractor)] = sent_to(adapters, site.contractor)
    assert to_client == (
        "NGN 8,000,000.00 for 'Foundation' on 4-bedroom bungalow has been released to your contractor."
    )
    assert to_contractor.startswith("NGN 8,000,000.00 for 'Foundation'")


async def test_missing_milestone_sends_nothing(db_session: AsyncSession) -> None:
    assert await notices.send_update(db_session, uuid.uuid4(), "claimed", "k9", adapters=fakes()) == []


async def test_unknown_event_is_a_programming_error(db_session: AsyncSession) -> None:
    with pytest.raises(ValueError, match="unknown milestone event"):
        await notices.send_update(db_session, uuid.uuid4(), "approved", "k10")


async def test_real_verify_and_release_queue_their_messages(db_session: AsyncSession, queued: Queued) -> None:
    site = await active_project(db_session, first_status=S.APPROVED)
    await service.mark_released(db_session, site.milestones[0].id)
    await db_session.commit()
    assert [e for _, e, _ in queued] == ["released"]


# --- daily reminders ----------------------------------------------------------------------------


async def test_reminders_for_slow_approvals_and_verifications(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    site = await active_project(db_session, first_status=S.VERIFIED)
    verified, claimed = site.milestones
    verified.verified_at = now - timedelta(days=3)
    claimed.status = S.CLAIMED
    claimed.claimed_at = now - timedelta(hours=30)
    await db_session.flush()

    adapters = fakes()
    counts = await notices.send_reminders(db_session, now=now, adapters=adapters)
    assert counts["client"] >= 1 and counts["supervisor"] >= 1
    [(_, to_client)] = sent_to(adapters, site.client)
    assert to_client == (
        "'Foundation' on 4-bedroom bungalow was verified 3 days ago and is waiting for your approval."
    )
    [(_, to_supervisor)] = sent_to(adapters, site.supervisor)
    assert to_supervisor.startswith(
        "'Roofing' on 4-bedroom bungalow has been waiting for your verification since"
    )

    # Run again the same day: nothing new for these milestones.
    again = fakes()
    await notices.send_reminders(db_session, now=now, adapters=again)
    assert sent_to(again, site.client) == [] and sent_to(again, site.supervisor) == []


async def test_no_reminder_before_the_wait_or_on_a_paused_project(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    fresh = await active_project(db_session, first_status=S.VERIFIED)
    fresh.milestones[0].verified_at = now - timedelta(hours=47)
    paused = await active_project(db_session, first_status=S.VERIFIED)
    paused.milestones[0].verified_at = now - timedelta(days=5)
    await db_session.flush()
    await set_project_status(db_session, paused.project_id, "paused")

    adapters = fakes()
    await notices.send_reminders(db_session, now=now, adapters=adapters)
    assert sent_to(adapters, fresh.client) == [] and sent_to(adapters, paused.client) == []


async def test_saved_rows_carry_the_milestone(db_session: AsyncSession) -> None:
    site = await claimed_site(db_session)
    rows = await notices.send_update(db_session, site.milestones[0].id, "claimed", "k11", adapters=fakes())
    row = rows[0]
    assert isinstance(row, Notification)
    assert row.template == "milestone.claimed.client"
    assert row.payload["milestone_id"] == str(site.milestones[0].id)
    assert row.payload["_key"] == "k11:main"
