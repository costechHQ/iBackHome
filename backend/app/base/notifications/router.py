"""HTTP endpoints for the signed-in user's own notification feed. Owner: Lilian.

Sending stays in notify(); these routes only read what a person was sent and mark it read.
"""

import uuid

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.base.notifications import service
from app.base.notifications.models import Notification
from app.base.notifications.schemas import FeedItem, FeedPage
from app.base.users import service as users
from app.core import pagination
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none

router = APIRouter(tags=["notifications"])


def _item(row: Notification) -> FeedItem:
    title, text = service.feed_words(row)
    return FeedItem(
        id=row.id,
        template=row.template,
        title=title,
        text=text,
        created_at=row.created_at,
        read_at=row.read_at,
    )


@router.get("/me/notifications", response_model=FeedPage)
async def my_notifications(
    session: SessionDep,
    user: users.CurrentUserDep,
    cursor: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=pagination.DEFAULT_LIMIT, ge=1, le=pagination.MAX_LIMIT),
) -> FeedPage:
    """Your notifications, newest first, with how many are unread."""
    rows, next_cursor, unread = await service.list_feed(session, user, cursor=cursor, limit=limit)
    return FeedPage(items=[_item(r) for r in rows], next_cursor=next_cursor, unread_count=unread)


@router.post("/me/notifications/{notification_id}/read", response_model=FeedItem)
async def read_notification(
    notification_id: uuid.UUID,
    session: SessionDep,
    user: users.CurrentUserDep,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Mark one of your notifications read. Doing it twice changes nothing."""
    scope = f"POST /me/notifications/{notification_id}/read {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    row = await service.mark_read(session, user, notification_id)
    out = _item(row).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)
