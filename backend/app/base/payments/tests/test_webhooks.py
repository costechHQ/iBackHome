"""Webhook safety: forged webhooks are refused, re-delivered ones are processed once.

Day 2 "done when": the same webhook sent twice creates one event.
"""

import asyncio
import time
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import Request
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.base.payments import service, webhooks
from app.base.payments.models import PaymentEvent
from app.base.payments.tests.webhook_helpers import (
    body,
    escrow_headers,
    paystack_headers,
    stripe_headers,
    webhook_secrets,
)

STRIPE_URL = "/api/v1/webhooks/stripe"
PAYSTACK_URL = "/api/v1/webhooks/paystack"
ESCROW_URL = "/api/v1/webhooks/escrow"


@pytest.fixture(autouse=True)
def _secrets(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with webhook_secrets(monkeypatch):
        yield


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Registers a counting handler for test.counted on every provider; returns the call list."""
    seen: list[str] = []

    async def counting(session: AsyncSession, event: PaymentEvent, request: Request | None) -> None:
        seen.append(event.event_id)

    for provider in ("stripe", "paystack", "escrow"):
        monkeypatch.setitem(webhooks._HANDLERS, (provider, "test.counted"), counting)
    return seen


def stripe_event(event_type: str = "test.counted", **data: Any) -> dict[str, Any]:
    return {"id": f"evt_{uuid.uuid4().hex}", "type": event_type, "data": {"object": data}}


def paystack_event(event_type: str = "test.counted") -> dict[str, Any]:
    return {"event": event_type, "data": {"id": int(time.time() * 1000) + uuid.uuid4().int % 10**6}}


async def stored(session: AsyncSession, provider: str, event_id: str) -> list[PaymentEvent]:
    rows = await session.scalars(
        select(PaymentEvent).where(PaymentEvent.provider == provider, PaymentEvent.event_id == event_id)
    )
    return list(rows)


# --- duplicates ------------------------------------------------------------------------------


async def test_same_stripe_event_twice_is_stored_and_handled_once(
    client: AsyncClient, db_session: AsyncSession, calls: list[str]
) -> None:
    raw = body(event := stripe_event())

    first = await client.post(STRIPE_URL, content=raw, headers=stripe_headers(raw))
    second = await client.post(STRIPE_URL, content=raw, headers=stripe_headers(raw))

    assert first.status_code == 200 and first.json() == {"received": True, "duplicate": False}
    assert second.status_code == 200 and second.json() == {"received": True, "duplicate": True}
    assert calls == [event["id"]]
    rows = await stored(db_session, "stripe", event["id"])
    assert len(rows) == 1
    assert rows[0].event_type == "test.counted" and rows[0].processed_at is not None


async def test_same_paystack_event_twice_is_stored_and_handled_once(
    client: AsyncClient, db_session: AsyncSession, calls: list[str]
) -> None:
    raw = body(event := paystack_event())

    first = await client.post(PAYSTACK_URL, content=raw, headers=paystack_headers(raw))
    second = await client.post(PAYSTACK_URL, content=raw, headers=paystack_headers(raw))

    assert (first.json()["duplicate"], second.json()["duplicate"]) == (False, True)
    event_id = f"test.counted:{event['data']['id']}"
    assert calls == [event_id]
    assert len(await stored(db_session, "paystack", event_id)) == 1


async def test_escrow_event_is_stored_and_handled(
    client: AsyncClient, db_session: AsyncSession, calls: list[str]
) -> None:
    raw = body(event := stripe_event())  # our escrow scheme uses the same id/type shape

    response = await client.post(ESCROW_URL, content=raw, headers=escrow_headers(raw))

    assert response.status_code == 200
    assert calls == [event["id"]]
    assert len(await stored(db_session, "escrow", event["id"])) == 1


async def test_same_event_id_from_two_providers_are_two_events(
    client: AsyncClient, db_session: AsyncSession, calls: list[str]
) -> None:
    raw = body(event := stripe_event())

    await client.post(STRIPE_URL, content=raw, headers=stripe_headers(raw))
    await client.post(ESCROW_URL, content=raw, headers=escrow_headers(raw))

    assert calls == [event["id"], event["id"]]


async def test_unknown_event_type_is_stored_and_acknowledged(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    raw = body(event := stripe_event("customer.created"))

    response = await client.post(STRIPE_URL, content=raw, headers=stripe_headers(raw))

    assert response.status_code == 200 and response.json()["duplicate"] is False
    [row] = await stored(db_session, "stripe", event["id"])
    assert row.processed_at is None  # stored, nothing to do yet
    assert row.payload == event


# --- forged or broken webhooks ---------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    ["tampered_body", "wrong_secret", "missing_header", "stale_timestamp", "garbage_header"],
)
async def test_bad_stripe_signature_is_refused_and_nothing_stored(
    client: AsyncClient, db_session: AsyncSession, calls: list[str], case: str
) -> None:
    raw = body(event := stripe_event())
    headers = {
        "tampered_body": stripe_headers(raw),
        "wrong_secret": stripe_headers(raw, secret="whsec_someone_else"),  # noqa: S106
        "missing_header": {"Content-Type": "application/json"},
        "stale_timestamp": stripe_headers(raw, timestamp=int(time.time()) - 600),
        "garbage_header": {"Stripe-Signature": "nonsense"},
    }[case]
    sent = raw.replace(b"test.counted", b"test.counteD") if case == "tampered_body" else raw

    response = await client.post(STRIPE_URL, content=sent, headers=headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_signature"
    assert calls == []
    assert await stored(db_session, "stripe", event["id"]) == []


@pytest.mark.parametrize("case", ["tampered_body", "wrong_secret", "missing_header"])
async def test_bad_paystack_signature_is_refused_and_nothing_stored(
    client: AsyncClient, db_session: AsyncSession, calls: list[str], case: str
) -> None:
    raw = body(event := paystack_event())
    headers = {
        "tampered_body": paystack_headers(raw),
        "wrong_secret": paystack_headers(raw, secret="sk_test_someone_else"),  # noqa: S106
        "missing_header": {"Content-Type": "application/json"},
    }[case]
    sent = raw.replace(b"test.counted", b"test.counteD") if case == "tampered_body" else raw

    response = await client.post(PAYSTACK_URL, content=sent, headers=headers)

    assert response.status_code == 400
    assert calls == []
    assert await stored(db_session, "paystack", f"test.counted:{event['data']['id']}") == []


async def test_bad_escrow_signature_is_refused(client: AsyncClient, calls: list[str]) -> None:
    raw = body(stripe_event())

    response = await client.post(ESCROW_URL, content=raw, headers=escrow_headers(raw, secret="nope"))  # noqa: S106

    assert response.status_code == 400
    assert calls == []


async def test_unset_secret_refuses_instead_of_accepting(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, calls: list[str]
) -> None:
    from app.base.payments.settings import get_payments_settings

    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "")
    get_payments_settings.cache_clear()
    raw = body(stripe_event())

    response = await client.post(STRIPE_URL, content=raw, headers=stripe_headers(raw))

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "webhook_not_configured"
    assert calls == []


async def test_signed_body_that_is_not_json_is_refused(client: AsyncClient) -> None:
    raw = b"not json"

    response = await client.post(STRIPE_URL, content=raw, headers=stripe_headers(raw))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "webhook_invalid_payload"


async def test_signed_body_without_id_or_type_is_refused(client: AsyncClient) -> None:
    raw = body({"hello": "world"})

    response = await client.post(STRIPE_URL, content=raw, headers=stripe_headers(raw))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "webhook_invalid_event"


# --- a failing handler leaves nothing behind -------------------------------------------------


async def test_handler_that_raises_leaves_no_event_so_the_retry_is_processed(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempts: list[str] = []

    async def flaky(session: AsyncSession, event: PaymentEvent, request: Request | None) -> None:
        attempts.append(event.event_id)
        if len(attempts) == 1:
            raise RuntimeError("downstream failed")

    monkeypatch.setitem(webhooks._HANDLERS, ("stripe", "test.flaky"), flaky)
    raw = body(event := stripe_event("test.flaky"))

    failed = await client.post(STRIPE_URL, content=raw, headers=stripe_headers(raw))
    assert failed.status_code == 500  # the provider will retry
    assert await stored(db_session, "stripe", event["id"]) == []

    retried = await client.post(STRIPE_URL, content=raw, headers=stripe_headers(raw))
    assert retried.status_code == 200 and retried.json()["duplicate"] is False
    assert attempts == [event["id"], event["id"]]
    [row] = await stored(db_session, "stripe", event["id"])
    assert row.processed_at is not None


# --- registry and record_event ---------------------------------------------------------------


def test_registering_a_second_handler_for_one_event_type_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhooks, "_HANDLERS", {})

    @webhooks.handles("stripe", "test.once")
    async def first(session: AsyncSession, event: PaymentEvent, request: Request | None) -> None: ...

    with pytest.raises(RuntimeError, match="already has a handler"):

        @webhooks.handles("stripe", "test.once")
        async def second(session: AsyncSession, event: PaymentEvent, request: Request | None) -> None: ...


async def test_record_event_returns_new_then_duplicate(db_session: AsyncSession) -> None:
    event_id = f"evt_{uuid.uuid4().hex}"

    first, event = await service.record_event(db_session, "stripe", event_id, "x.y", {"id": event_id})
    again, none = await service.record_event(db_session, "stripe", event_id, "x.y", {"id": event_id})

    assert first is service.EventResult.NEW and event is not None and event.processed_at is None
    assert again is service.EventResult.DUPLICATE and none is None


async def test_concurrent_deliveries_record_one_event(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Two deliveries racing on separate connections: exactly one is NEW (real commits)."""
    event_id = f"evt_race_{uuid.uuid4().hex}"

    async def deliver() -> service.EventResult:
        async with session_factory() as session:
            result, _ = await service.record_event(session, "stripe", event_id, "x.y", {"id": event_id})
            await asyncio.sleep(0.05)  # hold the row so the other delivery has to wait on it
            await session.commit()
            return result

    try:
        results = await asyncio.gather(deliver(), deliver())
        assert sorted(results) == [service.EventResult.DUPLICATE, service.EventResult.NEW]
        async with session_factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(PaymentEvent).where(PaymentEvent.event_id == event_id)
            )
        assert count == 1
    finally:
        async with session_factory() as session:
            await session.execute(delete(PaymentEvent).where(PaymentEvent.event_id == event_id))
            await session.commit()
