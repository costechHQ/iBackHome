"""Telling people about milestone changes.

`transition()` calls schedule() for every move. For the moves people hear about (claimed, verified,
claim rejected, released) it queues the `milestones.send_update` task to run only after the
transaction commits, so nobody is told about a change that was rolled back. The task calls
send_update(), which looks the milestone up again and notifies each person (messages.py has who
hears what). Every send has a key, so a task that runs twice sends nothing new.

send_reminders() is the daily `milestones.remind` job.
"""

import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications import Template, notify
from app.base.notifications.adapters import Adapter
from app.base.notifications.models import Channel, Notification
from app.base.payments.after_commit import after_commit
from app.base.users import service as users
from app.base.users.models import User
from app.features.milestones import messages
from app.features.milestones.models import Milestone, MilestoneStatus, Verification
from app.features.projects import service as projects

log = logging.getLogger(__name__)

S = MilestoneStatus

CLAIMED, VERIFIED, REJECTED, RELEASED = "claimed", "verified", "rejected", "released"
EVENTS = (CLAIMED, VERIFIED, REJECTED, RELEASED)

# "push" in the spec's table: push first, then the usual fallback.
PUSH_FIRST = ("push", "whatsapp", "sms", "email")
EMAIL_ONLY = ("email",)

CLIENT_APPROVAL_WAIT = timedelta(hours=48)
SUPERVISOR_VERIFY_WAIT = timedelta(hours=24)


def event_for(from_status: MilestoneStatus, to_status: MilestoneStatus) -> str | None:
    """Which message a move sends, if any."""
    if to_status == S.CLAIMED:
        return CLAIMED
    if to_status == S.VERIFIED:
        return VERIFIED
    if to_status == S.RELEASED:
        return RELEASED
    if from_status == S.CLAIMED and to_status == S.FUNDED:
        return REJECTED
    return None


def _stamp(milestone: Milestone, event: str) -> datetime | None:
    return {
        CLAIMED: milestone.claimed_at,
        VERIFIED: milestone.verified_at,
        RELEASED: milestone.released_at,
        REJECTED: milestone.funded_at,  # a rejection restamps funded_at
    }[event]


def schedule(session: AsyncSession, milestone: Milestone, from_status: MilestoneStatus) -> None:
    """Called by transition(): queue the message for this move once the transaction commits."""
    event = event_for(from_status, milestone.status)
    if event is None:
        return
    stamp = _stamp(milestone, event)
    key = f"{event}:{milestone.id}:{stamp.isoformat() if stamp else ''}"
    after_commit(session, enqueue_update, milestone.id, event, key)


def enqueue_update(milestone_id: uuid.UUID, event: str, key: str) -> None:
    """Queue milestones.send_update. A queue outage must not break the milestone change: it logs."""
    from app.features.milestones.tasks import send_update_task

    try:
        send_update_task.delay(str(milestone_id), event, key)
    except Exception:
        log.exception("could not queue the %s message for milestone %s", event, milestone_id)


def format_amount(amount_minor: int, currency: str) -> str:
    """e.g. 800000000, "NGN" -> "NGN 8,000,000.00" (integers only, never floats)."""
    major, minor = divmod(amount_minor, 100)
    return f"{currency} {major:,}.{minor:02d}"


@dataclass(frozen=True)
class _Send:
    user_id: uuid.UUID | None
    template: Template
    channels: tuple[str, ...] | None  # None = the default order (WhatsApp first)
    label: str  # part of the key, so "WhatsApp" and "+ email" to one person are two sends


async def _reason(session: AsyncSession, milestone_id: uuid.UUID) -> str:
    notes = await session.scalar(
        select(Verification.notes)
        .where(Verification.milestone_id == milestone_id, Verification.decision == "rejected")
        .order_by(Verification.created_at.desc(), Verification.id.desc())
        .limit(1)
    )
    return (notes or "see the supervisor's notes").strip().rstrip(".")


async def _name(session: AsyncSession, user_id: uuid.UUID | None, fallback: str) -> str:
    user: User | None = await users.get_user(session, user_id) if user_id else None
    return (user.full_name or fallback) if user else fallback


async def send_update(
    session: AsyncSession,
    milestone_id: uuid.UUID,
    event: str,
    key: str,
    *,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> list[Notification]:
    """Notify everyone who hears about `event` on this milestone. The caller commits.

    Returns the saved notification rows (an already-sent key returns the first row again).
    A milestone that no longer exists sends nothing.
    """
    if event not in EVENTS:
        raise ValueError(f"unknown milestone event {event!r}")
    milestone = await session.get(Milestone, milestone_id)
    if milestone is None:
        log.warning("milestones.send_update: milestone %s not found", milestone_id)
        return []
    project = await projects.get_project(session, milestone.project_id)
    data = {
        "milestone": milestone.name,
        "project": project.title,
        "amount": format_amount(milestone.amount_minor, milestone.currency),
        "contractor": await _name(session, project.contractor_id, "Your contractor"),
        "milestone_id": str(milestone.id),
        "project_id": str(project.id),
    }
    if event == REJECTED:
        data["reason"] = await _reason(session, milestone.id)

    sends = {
        CLAIMED: [
            _Send(project.client_id, messages.CLAIMED_CLIENT, None, "main"),
            _Send(project.supervisor_id, messages.CLAIMED_SUPERVISOR, PUSH_FIRST, "main"),
        ],
        VERIFIED: [
            _Send(project.client_id, messages.VERIFIED_CLIENT, None, "main"),
            _Send(project.client_id, messages.VERIFIED_CLIENT, EMAIL_ONLY, "email"),
            _Send(project.contractor_id, messages.VERIFIED_CONTRACTOR, PUSH_FIRST, "main"),
        ],
        REJECTED: [_Send(project.contractor_id, messages.REJECTED_CONTRACTOR, PUSH_FIRST, "main")],
        RELEASED: [
            _Send(project.client_id, messages.RELEASED_CLIENT, None, "main"),
            _Send(project.client_id, messages.RELEASED_CLIENT, EMAIL_ONLY, "email"),
            _Send(project.contractor_id, messages.RELEASED_CONTRACTOR, None, "main"),
        ],
    }[event]

    rows: list[Notification] = []
    for send in sends:
        if send.user_id is None:  # e.g. no supervisor assigned yet
            continue
        if send.channels == EMAIL_ONLY:
            user = await users.get_user(session, send.user_id)
            already_emailed = any(r.user_id == send.user_id and r.channel == "email" for r in rows)
            if user is None or not user.email or already_emailed:
                continue  # no address, or the first message already fell back to email
        rows.append(
            await notify(
                session,
                send.user_id,
                send.template,
                data,
                send.channels,
                key=f"{key}:{send.label}",
                adapters=adapters,
            )
        )
    return rows


async def send_reminders(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> dict[str, int]:
    """The daily reminders on active projects (spec: milestones.remind, 09:00 WAT):

    - clients, for milestones verified more than 48 hours ago and still waiting for approval;
    - the assigned supervisor, for claims waiting more than 24 hours for verification.

    At most one reminder per milestone per day. The caller commits. Returns counts.
    """
    now = now or datetime.now(UTC)
    today = now.date().isoformat()
    waiting = await session.scalars(
        select(Milestone).where(
            ((Milestone.status == S.VERIFIED) & (Milestone.verified_at <= now - CLIENT_APPROVAL_WAIT))
            | ((Milestone.status == S.CLAIMED) & (Milestone.claimed_at <= now - SUPERVISOR_VERIFY_WAIT))
        )
    )
    counts = {"client": 0, "supervisor": 0}
    for milestone in list(waiting):
        project = await projects.get_project(session, milestone.project_id)
        if project.status != "active":
            continue
        data = {"milestone": milestone.name, "project": project.title, "milestone_id": str(milestone.id)}
        if milestone.status == S.VERIFIED and milestone.verified_at is not None:
            days = (now - milestone.verified_at).days
            await notify(
                session,
                project.client_id,
                messages.REMIND_CLIENT,
                {**data, "days": days},
                key=f"remind:{milestone.id}:verified:{today}",
                adapters=adapters,
            )
            counts["client"] += 1
        elif milestone.status == S.CLAIMED and milestone.claimed_at is not None and project.supervisor_id:
            await notify(
                session,
                project.supervisor_id,
                messages.REMIND_SUPERVISOR,
                {**data, "claimed_on": milestone.claimed_at.strftime("%d %b %Y")},
                PUSH_FIRST,
                key=f"remind:{milestone.id}:claimed:{today}",
                adapters=adapters,
            )
            counts["supervisor"] += 1
    return counts
