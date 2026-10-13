"""HTTP endpoints for audit.

GET /api/v1/ops/audit: ops only. Newest first, filtered by any mix of the query parameters,
paginated with ?cursor=&limit= (pass back `next_cursor` to get the next page).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.base.audit import service
from app.base.audit.schemas import AuditEntryOut, AuditPage
from app.base.users import service as users
from app.core.db import SessionDep

router = APIRouter(tags=["audit"])


@router.get("/ops/audit", response_model=AuditPage, dependencies=[Depends(users.require_role("ops"))])
async def search_audit_log(
    session: SessionDep,
    actor_id: uuid.UUID | None = None,
    action: str | None = Query(default=None, max_length=80),
    object_type: str | None = Query(default=None, max_length=60),
    object_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    cursor: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=service.MAX_PAGE),
) -> AuditPage:
    entries, next_cursor = await service.search(
        session,
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        since=since,
        until=until,
        cursor=cursor,
        limit=limit,
    )
    return AuditPage(items=[AuditEntryOut.model_validate(e) for e in entries], next_cursor=next_cursor)
