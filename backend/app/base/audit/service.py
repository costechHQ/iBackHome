"""The audit log.

Every state change in the app writes one entry, in the same transaction as the change:

    from app.base import audit

    before = audit.snapshot(order)
    order.status = "approved"
    await audit.record(
        session, actor.id, "order.approved", "order", order.id,
        before=before, after=audit.snapshot(order), request=request,
    )
    await session.commit()   # the change and its audit entry are saved together

`record()` does not commit; the caller does. Use `actor_id=None` for things the system does
(webhooks, scheduled jobs). Name actions "<object>.<what happened>", e.g. "milestone.claimed".
Never put secrets (OTPs, tokens, keys) in `before`/`after`.
"""

import base64
import binascii
import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import instance_state

from app.base.audit.models import AuditEntry
from app.core.errors import AppError

DEVICE_HEADER = "X-Device-Id"
MAX_PAGE = 200


def snapshot(obj: object) -> dict[str, Any]:
    """The object's database columns as JSON-safe values, for `before` / `after`.

    Only columns already loaded are included, so this never triggers a database query.
    """
    state = instance_state(obj)
    loaded = state.dict
    values = {attr.key: loaded[attr.key] for attr in state.mapper.column_attrs if attr.key in loaded}
    result: dict[str, Any] = jsonable_encoder(values)
    return result


def _request_details(request: Request | None) -> tuple[str | None, str | None]:
    if request is None:
        return None, None
    ip = request.client.host if request.client else None
    device_id = request.headers.get(DEVICE_HEADER)
    return (ip[:45] if ip else None), (device_id[:128] if device_id else None)


async def record(
    session: AsyncSession,
    actor_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
    request: Request | None = None,
) -> AuditEntry:
    """Add one audit entry to the current transaction (the caller commits)."""
    ip, device_id = _request_details(request)
    entry = AuditEntry(
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=jsonable_encoder(dict(before)) if before is not None else None,
        after=jsonable_encoder(dict(after)) if after is not None else None,
        ip=ip,
        device_id=device_id,
    )
    session.add(entry)
    await session.flush()
    return entry


# --- search (GET /ops/audit) ----------------------------------------------------------------


def encode_cursor(entry: AuditEntry) -> str:
    raw = f"{entry.at.isoformat()}|{entry.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        at_text, id_text = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(at_text), uuid.UUID(id_text)
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise AppError("invalid_cursor", "The cursor is not valid. Start again without it.", 422) from exc


async def search(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    object_type: str | None = None,
    object_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[list[AuditEntry], str | None]:
    """Newest first. Returns one page and the cursor for the next page (None on the last page)."""
    if not 1 <= limit <= MAX_PAGE:
        raise AppError("invalid_limit", f"limit must be between 1 and {MAX_PAGE}.", 422)

    query = select(AuditEntry)
    if actor_id is not None:
        query = query.where(AuditEntry.actor_id == actor_id)
    if action is not None:
        query = query.where(AuditEntry.action == action)
    if object_type is not None:
        query = query.where(AuditEntry.object_type == object_type)
    if object_id is not None:
        query = query.where(AuditEntry.object_id == object_id)
    if since is not None:
        query = query.where(AuditEntry.at >= since)
    if until is not None:
        query = query.where(AuditEntry.at < until)
    if cursor is not None:
        cursor_at, cursor_id = decode_cursor(cursor)
        query = query.where(tuple_(AuditEntry.at, AuditEntry.id) < tuple_(cursor_at, cursor_id))

    query = query.order_by(AuditEntry.at.desc(), AuditEntry.id.desc()).limit(limit + 1)
    rows = list(await session.scalars(query))
    if len(rows) > limit:
        page = rows[:limit]
        return page, encode_cursor(page[-1])
    return rows, None
