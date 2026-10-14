"""Cursor pagination for list endpoints (`?cursor=&limit=`, as the spec requires).

Lists are ordered newest first by (timestamp, id). The cursor is the last row's pair, so a page
never repeats or skips a row even when new rows arrive between requests.

    from app.core import pagination

    if cursor is not None:
        at, row_id = pagination.decode_cursor(cursor)
        query = query.where(tuple_(Thing.created_at, Thing.id) < tuple_(at, row_id))
    rows = list(await session.scalars(query.order_by(...desc()).limit(limit + 1)))
    page, next_cursor = pagination.page(rows, limit, lambda t: (t.created_at, t.id))
"""

import base64
import binascii
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime

from app.core.errors import AppError

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def encode_cursor(at: datetime, row_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{at.isoformat()}|{row_id}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """422 invalid_cursor for anything this module didn't produce."""
    try:
        at_text, id_text = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(at_text), uuid.UUID(id_text)
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise AppError("invalid_cursor", "The cursor is not valid. Start again without it.", 422) from exc


def page[T](
    rows: Sequence[T], limit: int, key: Callable[[T], tuple[datetime, uuid.UUID]]
) -> tuple[list[T], str | None]:
    """Split `limit + 1` fetched rows into one page and the cursor for the next (None on the last page)."""
    if len(rows) > limit:
        items = list(rows[:limit])
        return items, encode_cursor(*key(items[-1]))
    return list(rows), None
