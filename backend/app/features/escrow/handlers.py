"""Webhook handlers for escrow, registered with base/payments' registry. Owner: Gabriel.

Imported by router.py, so they are registered when the app starts. Each handler runs inside the
webhook's transaction (event row + ledger + state + audit, or nothing) and never commits.
"""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import webhooks
from app.base.payments.models import PaymentEvent
from app.features.escrow import service


@webhooks.handles("stripe", "checkout.session.completed", "checkout.session.async_payment_succeeded")
async def on_checkout_paid(session: AsyncSession, event: PaymentEvent, request: Request | None) -> None:
    """A client's Stripe payment for a milestone: record it, hold it in escrow, mark it funded."""
    await service.fund_from_checkout(session, event, request)
