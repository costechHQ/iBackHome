"""Stripe Billing for the supervision subscription, behind one small interface. Owner: Gabriel.

    gateway = get_billing_gateway()           # a FastAPI dependency; tests override it
    checkout = await gateway.create_subscription_checkout(SubscriptionCheckoutRequest(...))
    await gateway.cancel_at_period_end("sub_...")

Like Checkout for funding, nothing counts until Stripe's signed webhooks arrive. This money is
iBackHome's own income, never escrow money (see features/subscriptions).
"""

from dataclasses import dataclass
from typing import Any, Protocol

import stripe

from app.base.payments.settings import get_payments_settings
from app.base.payments.stripe_checkout import CheckoutSession
from app.core.errors import AppError


@dataclass(frozen=True)
class SubscriptionCheckoutRequest:
    currency: str  # ISO 4217, upper case ("GBP"); Stripe gets it lower case
    amount_minor: int  # charged every month
    product_name: str
    metadata: dict[str, str]  # copied onto the Stripe subscription, so its webhooks find the project
    success_url: str
    cancel_url: str
    client_reference_id: str
    customer_email: str | None = None
    idempotency_key: str | None = None


class BillingGateway(Protocol):
    async def create_subscription_checkout(self, request: SubscriptionCheckoutRequest) -> CheckoutSession: ...

    async def cancel_at_period_end(self, subscription_id: str) -> None: ...


class StripeBilling:
    """The real Stripe API (test mode with an sk_test_ key)."""

    def __init__(self, secret_key: str) -> None:
        self._client = stripe.StripeClient(
            secret_key, http_client=stripe.HTTPXClient(allow_sync_methods=False)
        )

    async def create_subscription_checkout(self, request: SubscriptionCheckoutRequest) -> CheckoutSession:
        params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": request.currency.lower(),
                        "unit_amount": request.amount_minor,
                        "recurring": {"interval": "month"},
                        "product_data": {"name": request.product_name},
                    },
                }
            ],
            "metadata": request.metadata,
            "subscription_data": {"metadata": request.metadata},
            "client_reference_id": request.client_reference_id,
            "success_url": request.success_url,
            "cancel_url": request.cancel_url,
        }
        if request.customer_email:
            params["customer_email"] = request.customer_email
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

    async def cancel_at_period_end(self, subscription_id: str) -> None:
        try:
            await self._client.v1.subscriptions.update_async(subscription_id, {"cancel_at_period_end": True})
        except stripe.StripeError as exc:
            raise AppError(
                "stripe_unavailable", "Stripe could not cancel the subscription. Try again.", 502
            ) from exc


def get_billing_gateway() -> BillingGateway:
    """FastAPI dependency: the Stripe gateway from STRIPE_SECRET_KEY. Tests override this."""
    secret_key = get_payments_settings().stripe_secret_key
    if not secret_key:
        raise AppError("stripe_not_configured", "STRIPE_SECRET_KEY is not set.", 503)
    return StripeBilling(secret_key)
