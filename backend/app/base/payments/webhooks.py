"""Webhook handler registry and the one processing path every webhook takes. Owner: Gabriel.

A feature registers a handler for a provider's event type; the webhook routes in router.py
verify the signature, then call `process()`:

    from app.base.payments import webhooks

    @webhooks.handles("stripe", "checkout.session.completed")
    async def on_checkout_completed(
        session: AsyncSession, event: PaymentEvent, request: Request | None
    ) -> None:
        ...  # ledger + state change + audit; never commit here

Handlers are found by import: put them in a module your router.py imports, so they are
registered when the app starts (main.py imports every router).
"""

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments.models import PaymentEvent
from app.base.payments.service import EventResult, Provider, mark_processed, record_event
from app.core.errors import AppError

Handler = Callable[[AsyncSession, PaymentEvent, Request | None], Awaitable[None]]

_HANDLERS: dict[tuple[str, str], Handler] = {}


def handles(provider: Provider, *event_types: str) -> Callable[[Handler], Handler]:
    """Register the decorated function for these event types. One handler per (provider, type)."""

    def register(handler: Handler) -> Handler:
        for event_type in event_types:
            existing = _HANDLERS.get((provider, event_type))
            if existing is not None and existing is not handler:
                raise RuntimeError(f"{provider} {event_type} already has a handler: {existing.__qualname__}")
            _HANDLERS[(provider, event_type)] = handler
        return handler

    return register


def handler_for(provider: str, event_type: str) -> Handler | None:
    return _HANDLERS.get((provider, event_type))


def event_identity(provider: Provider, payload: Mapping[str, Any]) -> tuple[str, str]:
    """(event_id, event_type) for a parsed webhook body.

    Stripe and our escrow scheme send `id` and `type`. Paystack sends no event id, so ours is
    "<event>:<data.id>": one row per transfer per outcome (a transfer's `transfer.success` and a
    later `transfer.reversed` are two events; the same `transfer.success` twice is one).
    """
    try:
        if provider == "paystack":
            event_type = str(payload["event"])
            return f"{event_type}:{payload['data']['id']}", event_type
        return str(payload["id"]), str(payload["type"])
    except (KeyError, TypeError) as exc:
        raise AppError("webhook_invalid_event", "The webhook has no event id or type.", 400) from exc


async def process(
    session: AsyncSession, provider: Provider, payload: Mapping[str, Any], request: Request | None = None
) -> EventResult:
    """Store the event once and run its handler, all inside one savepoint.

    - Already stored: DUPLICATE, nothing runs.
    - No handler for this type: stored with processed_at NULL ("received, nothing to do yet").
    - Handler raises: the savepoint rolls back, so no event row is left and the provider's retry
      is processed in full; the exception reaches the route (5xx, so the provider retries).

    The caller commits.
    """
    event_id, event_type = event_identity(provider, payload)
    async with session.begin_nested():
        result, event = await record_event(session, provider, event_id, event_type, payload)
        if event is None:
            return result
        handler = handler_for(provider, event_type)
        if handler is not None:
            await handler(session, event, request)
            await mark_processed(session, event)
    return result
