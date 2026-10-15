"""Webhook handlers owned by payments itself (Paystack transfers). Owner: Gabriel.

Imported by router.py, so they are registered when the app starts.
"""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import service, webhooks
from app.base.payments.models import PaymentEvent


@webhooks.handles("paystack", *service.TRANSFER_EVENTS)
async def on_transfer_outcome(session: AsyncSession, event: PaymentEvent, request: Request | None) -> None:
    """transfer.success / transfer.failed / transfer.reversed: update the payout's status."""
    await service.apply_transfer_event(session, event, request)
