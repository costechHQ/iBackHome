"""Idempotency-Key: the same key for the same endpoint never does the work twice."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.idempotency import remember, replay_or_none

SCOPE = "POST /milestones/123/claim"


async def test_saved_response_is_replayed(db_session: AsyncSession) -> None:
    await remember(db_session, "key-1", SCOPE, 201, {"status": "claimed"})

    replay = await replay_or_none(db_session, "key-1", SCOPE)

    assert replay is not None
    assert replay.status_code == 201
    assert replay.body == b'{"status":"claimed"}'


async def test_new_key_has_nothing_to_replay(db_session: AsyncSession) -> None:
    assert await replay_or_none(db_session, "never-used", SCOPE) is None


async def test_missing_key_is_neither_saved_nor_replayed(db_session: AsyncSession) -> None:
    await remember(db_session, None, SCOPE, 200, {"ok": True})
    assert await replay_or_none(db_session, None, SCOPE) is None


async def test_same_key_on_another_endpoint_is_independent(db_session: AsyncSession) -> None:
    await remember(db_session, "key-2", SCOPE, 200, {"a": 1})
    await remember(db_session, "key-2", "POST /orders/9/approve", 200, {"b": 2})

    other = await replay_or_none(db_session, "key-2", "POST /orders/9/approve")
    assert other is not None and other.body == b'{"b":2}'


async def test_key_already_taken_is_409_not_500(db_session: AsyncSession) -> None:
    # What a second request sees when another one with the same key got there first.
    await remember(db_session, "key-3", SCOPE, 200, {"first": True})

    with pytest.raises(AppError) as error:
        await remember(db_session, "key-3", SCOPE, 200, {"second": True})

    assert error.value.status_code == 409
    assert error.value.code == "idempotency_key_in_use"
    # Only the savepoint was rolled back: the first response is still there.
    replay = await replay_or_none(db_session, "key-3", SCOPE)
    assert replay is not None and replay.body == b'{"first":true}'
