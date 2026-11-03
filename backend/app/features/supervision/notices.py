"""Telling a supervisor about a spot check ops scheduled for them (spec: push + SMS).

schedule_spot_check() calls schedule(), which queues `supervision.notify_spot_check` to run only after the
transaction commits, so nobody is told about a visit that was rolled back. The task calls send_assigned(),
which looks the spot check up again. Every send has a key, so a task that runs twice sends nothing new.

Push goes first. A supervisor with no registered phone, or with push switched off, gets the SMS instead of
push; one whose push worked gets the SMS as well, because spot-check SMS is required and cannot be turned off.
"""

import logging
import uuid
from collections.abc import Mapping
from datetime import timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications import notify
from app.base.notifications.adapters import Adapter
from app.base.notifications.models import Channel, Notification
from app.base.payments.after_commit import after_commit
from app.features.projects import service as projects
from app.features.supervision import messages
from app.features.supervision.models import SpotCheck

log = logging.getLogger(__name__)

WAT = timezone(timedelta(hours=1))  # Nigerian time: what the supervisor reads


def schedule(session: AsyncSession, spot_check: SpotCheck) -> None:
    """Queue the message for this spot check once the transaction commits."""
    after_commit(session, enqueue, spot_check.id)


def enqueue(spot_check_id: uuid.UUID) -> None:
    """Queue supervision.notify_spot_check. A queue outage must not break scheduling: it logs."""
    from app.features.supervision.tasks import notify_spot_check_task

    try:
        notify_spot_check_task.delay(str(spot_check_id))
    except Exception:
        log.exception("could not queue the message for spot check %s", spot_check_id)


def when_text(spot_check: SpotCheck) -> str:
    """e.g. "Tue 04 Nov, 09:30 (Nigerian time)"."""
    return spot_check.scheduled_for.astimezone(WAT).strftime("%a %d %b, %H:%M") + " (Nigerian time)"


async def send_assigned(
    session: AsyncSession,
    spot_check_id: uuid.UUID,
    *,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> list[Notification]:
    """Tell the visiting supervisor (push, then SMS). The caller commits. A missing or finished spot check
    sends nothing."""
    spot_check = await session.get(SpotCheck, spot_check_id)
    if spot_check is None or spot_check.completed_at is not None:
        return []
    project = await projects.get_project(session, spot_check.project_id)
    data = {
        "project": project.title,
        "when": when_text(spot_check),
        "spot_check_id": str(spot_check.id),
        "project_id": str(project.id),
    }
    key = f"assigned:{spot_check.id}"
    first = await notify(
        session, spot_check.supervisor_id, messages.SPOT_CHECK_ASSIGNED, data,
        ("push", "sms"), key=f"{key}:main", adapters=adapters,
    )  # fmt: skip
    rows = [first]
    if first.channel == Channel.PUSH.value:
        rows.append(
            await notify(
                session,
                spot_check.supervisor_id,
                messages.SPOT_CHECK_ASSIGNED,
                data,
                ("sms",),
                key=f"{key}:sms",
                adapters=adapters,
            )  # fmt: skip
        )
    return rows
