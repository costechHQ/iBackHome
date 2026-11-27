"""Telling people about a match request (ADR 0007, phase 2). Owner: Christopher.

Everything is queued to run only after the transaction commits (payments' after_commit helper), so nobody is
told about something that was rolled back. Each message is sent once:

- ops are emailed when a client asks (marked on the request, so a retried job never repeats it);
- the client is told when a shortlist is ready, once per shortlist (`notify(..., key=)`);
- the contractor is told when a client chooses them, once.
"""

import hashlib
import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications import notify, notify_address
from app.base.notifications.adapters import Adapter
from app.base.notifications.models import Channel
from app.base.users import service as users
from app.core.errors import AppError
from app.features.contractors import messages
from app.features.contractors.models import MatchRequest, MatchShortlist
from app.features.contractors.settings import get_contractor_settings
from app.features.projects import service as projects

log = logging.getLogger(__name__)


def enqueue_ops_email(request_id: uuid.UUID) -> None:
    """Queue the ops email. A queue outage must not break the request: it is saved, so this only logs."""
    from app.features.contractors.tasks import send_match_request_email_task

    try:
        send_match_request_email_task.delay(str(request_id))
    except Exception:
        log.exception("could not queue the ops email for match request %s", request_id)


def enqueue_notice(request_id: uuid.UUID, kind: str) -> None:
    from app.features.contractors.tasks import send_match_notice_task

    try:
        send_match_notice_task.delay(str(request_id), kind)
    except Exception:
        log.exception("could not queue the %s message for match request %s", kind, request_id)


def _money(minor: int, currency: str) -> str:
    return f"{currency} {minor // 100:,}.{minor % 100:02d}"


async def send_ops_email(
    session: AsyncSession, request_id: uuid.UUID, *, adapters: Mapping[Channel, Adapter] | None = None
) -> bool:
    """Email ops the brief, once. True when sent (or nothing to send); False means try again later."""
    row = await session.get(MatchRequest, request_id)
    if row is None or row.ops_emailed_at is not None:
        return True
    project = await projects.get_project(session, row.project_id)
    client = await users.get_user(session, row.client_id)
    who = (client.full_name or client.phone or client.email or "a client") if client else "a client"
    data = {
        "project_title": project.title,
        "address": project.address,
        "budget": _money(row.budget_minor, row.currency),
        "city": row.city,
        "state": row.state,
        "work_type": row.work_type,
        "timeline": row.timeline,
        "notes": row.notes or "none",
        "client": who,
        "request_id": row.id,
    }
    try:
        await notify_address(
            session,
            get_contractor_settings().ops_notify_email,
            "email",
            messages.MATCH_REQUESTED_OPS,
            data,
            adapters=adapters,
        )
    except AppError as exc:
        digest = hashlib.sha256(get_contractor_settings().ops_notify_email.encode()).hexdigest()[:8]
        log.warning("match request email to %s not sent (%s); will retry", digest, exc.code)
        return False
    row.ops_emailed_at = datetime.now(UTC)
    await session.commit()
    return True


async def send_notice(
    session: AsyncSession,
    request_id: uuid.UUID,
    kind: str,
    *,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> None:
    """Tell the client their shortlist is ready ("shortlist"), or the contractor they were chosen ("chosen").

    The caller commits. Each is sent once (a key per shortlist, or per request). A request that has moved
    on since (cancelled, or the shortlist replaced) sends nothing.
    """
    row = await session.get(MatchRequest, request_id)
    if row is None:
        return
    project = await projects.get_project(session, row.project_id)
    if kind == "shortlist":
        if row.status != "shortlisted":
            return
        count = len(
            list(await session.scalars(select(MatchShortlist.id).where(MatchShortlist.request_id == row.id)))
        )
        await notify(
            session,
            row.client_id,
            messages.MATCH_SHORTLIST_READY,
            {"count": count, "project": project.title, "project_id": str(project.id)},
            key=f"shortlist:{row.id}:{row.shortlist_version}",
            adapters=adapters,
        )
    elif kind == "chosen":
        if row.status != "matched" or row.chosen_contractor_id is None:
            return
        await notify(
            session,
            row.chosen_contractor_id,
            messages.MATCH_CONTRACTOR_CHOSEN,
            {"project": project.title, "project_id": str(project.id)},
            key=f"chosen:{row.id}",
            adapters=adapters,
        )
