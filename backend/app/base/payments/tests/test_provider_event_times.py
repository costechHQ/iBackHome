"""payments.provider_event_times(): when the provider says a stored event happened."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import provider_event_times, record_event


async def stored(session: AsyncSession, provider: str, payload: dict[str, object]) -> uuid.UUID:
    _, event = await record_event(
        session,
        provider,  # type: ignore[arg-type]
        f"evt_{uuid.uuid4().hex}",
        "checkout.session.completed",
        payload,
    )
    assert event is not None
    return event.id


async def test_stripe_event_time_comes_from_created(db_session: AsyncSession) -> None:
    happened = datetime(2026, 10, 14, 23, 59, 30, tzinfo=UTC)
    event_id = await stored(db_session, "stripe", {"id": "evt", "created": int(happened.timestamp())})
    assert await provider_event_times(db_session, [event_id]) == {event_id: happened}


async def test_without_created_it_is_when_we_stored_it(db_session: AsyncSession) -> None:
    event_id = await stored(db_session, "paystack", {"event": "transfer.success", "data": {}})
    [when] = (await provider_event_times(db_session, [event_id])).values()
    assert abs((datetime.now(UTC) - when).total_seconds()) < 120


async def test_unknown_ids_are_left_out(db_session: AsyncSession) -> None:
    assert await provider_event_times(db_session, [uuid.uuid4()]) == {}
    assert await provider_event_times(db_session, []) == {}
