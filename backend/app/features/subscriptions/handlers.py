"""Stripe webhook handlers for subscriptions, registered with base/payments' registry. Owner: Christopher.

Imported by router.py, so they are registered when the app starts. Each handler runs inside the
webhook's transaction (event row + ledger + state + audit, or nothing) and never commits.

`checkout.session.completed` is not handled here: escrow owns that event for funding, and the
subscription's own events (below) carry everything we need.
"""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import webhooks
from app.base.payments.models import PaymentEvent
from app.features.subscriptions import service


@webhooks.handles(
    "stripe",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
)
async def on_subscription_changed(
    session: AsyncSession, event: PaymentEvent, request: Request | None
) -> None:
    await service.apply_subscription_event(session, event, request)


@webhooks.handles("stripe", "invoice.paid", "invoice.payment_failed")
async def on_invoice(session: AsyncSession, event: PaymentEvent, request: Request | None) -> None:
    await service.apply_invoice_event(session, event, request)
