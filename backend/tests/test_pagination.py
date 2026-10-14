"""core/pagination: cursors round-trip, bad cursors are 422, and pages split at `limit`."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core import pagination
from app.core.errors import AppError


def test_cursor_round_trips() -> None:
    at, row_id = datetime(2026, 10, 14, 9, 30, 1, 123456, tzinfo=UTC), uuid.uuid4()
    assert pagination.decode_cursor(pagination.encode_cursor(at, row_id)) == (at, row_id)


@pytest.mark.parametrize(
    "cursor", ["", "not-a-cursor", "!!!", pagination.encode_cursor(datetime.now(UTC), uuid.uuid4())[:-4]]
)
def test_bad_cursor_is_422(cursor: str) -> None:
    with pytest.raises(AppError) as caught:
        pagination.decode_cursor(cursor)
    assert (caught.value.code, caught.value.status_code) == ("invalid_cursor", 422)


def test_page_splits_at_limit() -> None:
    start = datetime(2026, 10, 14, tzinfo=UTC)
    rows = [(start - timedelta(minutes=i), uuid.uuid4()) for i in range(3)]

    items, cursor = pagination.page(rows, 2, lambda r: r)
    assert items == rows[:2]
    assert cursor is not None and pagination.decode_cursor(cursor) == rows[1]

    items, cursor = pagination.page(rows[:2], 2, lambda r: r)
    assert items == rows[:2] and cursor is None
