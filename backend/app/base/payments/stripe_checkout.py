"""Stripe Checkout, behind one small interface so tests never call Stripe. Owner: Gabriel.

    gateway = get_checkout_gateway()          # a FastAPI dependency; tests override it
    checkout = await gateway.create_checkout_session(CheckoutRequest(...))
    checkout.url                              # send the client here to pay

Money only counts when Stripe's signed `checkout.session.completed` webhook arrives; creating a
session records nothing in the ledger.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

import stripe

from app.base.payments.settings import get_payments_settings
from app.core.errors import AppError


@dataclass(frozen=True)
class LineItem:
    name: str
    amount_minor: int  # unit_amount in the session's currency


@dataclass(frozen=True)
class CheckoutRequest:
    currency: str  # ISO 4217, upper case ("GBP"); Stripe gets it lower case
    line_items: list[LineItem]
    metadata: dict[str, str]  # Stripe: string values only, at most 50 keys
    success_url: str
    cancel_url: str
    client_reference_id: str
    customer_email: str | None = None
    idempotency_key: str | None = None  # passed to Stripe so a retried create returns the same session
    expires_at: int | None = field(default=None)  # unix seconds; None = Stripe's default (24 h)

    @property
    def amount_total_minor(self) -> int:
        return sum(item.amount_minor for item in self.line_items)


@dataclass(frozen=True)
class CheckoutSession:
    id: str  # cs_test_...
    url: str


class CheckoutGateway(Protocol):
    async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSession: ...


class StripeCheckout:
    """The real Stripe API (test mode with an sk_test_ key)."""

    def __init__(self, secret_key: str) -> None:
        self._client = stripe.StripeClient(
            secret_key, http_client=stripe.HTTPXClient(allow_sync_methods=False)
        )

    async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSession:
        params: dict[str, Any] = {
            "mode": "payment",
            "line_items": [
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": request.currency.lower(),
                        "unit_amount": item.amount_minor,
                        "product_data": {"name": item.name},
                    },
                }
                for item in request.line_items
            ],
            "metadata": request.metadata,
            "payment_intent_data": {"metadata": request.metadata},
            "client_reference_id": request.client_reference_id,
            "success_url": request.success_url,
            "cancel_url": request.cancel_url,
        }
        if request.customer_email:
            params["customer_email"] = request.customer_email
        if request.expires_at is not None:
            params["expires_at"] = request.expires_at
        options: dict[str, Any] = {}
        if request.idempotency_key:
            options["idempotency_key"] = request.idempotency_key
        try:
            session = await self._client.v1.checkout.sessions.create_async(params, options)  # type: ignore[arg-type]
        except stripe.StripeError as exc:
            raise AppError(
                "stripe_unavailable", "Stripe could not create the payment page. Try again.", 502
            ) from exc
        if not session.url:
            raise AppError("stripe_unavailable", "Stripe returned no payment page URL.", 502)
        return CheckoutSession(id=session.id, url=session.url)


def get_checkout_gateway() -> CheckoutGateway:
    """FastAPI dependency: the Stripe gateway from STRIPE_SECRET_KEY. Tests override this."""
    secret_key = get_payments_settings().stripe_secret_key
    if not secret_key:
        raise AppError("stripe_not_configured", "STRIPE_SECRET_KEY is not set.", 503)
    return StripeCheckout(secret_key)
