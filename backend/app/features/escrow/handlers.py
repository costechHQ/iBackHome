"""Webhook handlers for escrow, registered with base/payments' registry. Owner: Gabriel.

Imported by router.py, so they are registered when the app starts. Each handler runs inside the
webhook's transaction (event row + ledger + state + audit, or nothing) and never commits.
"""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import payments
from app.base.payments import webhooks
from app.base.payments.models import PaymentEvent, Payout
from app.features.escrow import service


@webhooks.handles("stripe", "checkout.session.completed", "checkout.session.async_payment_succeeded")
async def on_checkout_paid(session: AsyncSession, event: PaymentEvent, request: Request | None) -> None:
    """A client's Stripe payment for a milestone: record it, hold it in escrow, mark it funded."""
    await service.fund_from_checkout(session, event, request)


@webhooks.handles("escrow", "release.succeeded", "release.failed")
async def on_release_outcome(session: AsyncSession, event: PaymentEvent, request: Request | None) -> None:
    """The escrow partner confirmed (or failed) a release we submitted."""
    await service.apply_release_event(session, event, request)


@payments.on_payout_outcome(service.PAYOUT_REFERENCE_PREFIX)
async def on_release_payout(
    session: AsyncSession, payout: Payout, previous: str, request: Request | None
) -> None:
    """A release's Paystack payout succeeded, failed or was reversed."""
    await service.on_release_payout(session, payout, previous, request)
