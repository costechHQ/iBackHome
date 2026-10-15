"""Webhook signature checks. Owner: Gabriel.

Each check runs on the RAW request body, before any JSON parsing, and raises AppError 400
`invalid_signature` when the signature is missing or wrong. A provider whose secret is not
configured is refused with 503 `webhook_not_configured`, so an unset secret can never mean
"accept anything".

- Stripe: `Stripe-Signature`, Stripe's scheme (HMAC-SHA256 of "<t>.<body>", refused when
  older than 5 minutes), secret STRIPE_WEBHOOK_SECRET.
- Paystack: `x-paystack-signature`, hex HMAC-SHA512 of the body, secret PAYSTACK_SECRET_KEY.
- Escrow: `X-Escrow-Signature`, hex HMAC-SHA256 of the body, secret ESCROW_WEBHOOK_SECRET
  (our own scheme until a partner signs; spec open decision 2).
"""

import hmac

import stripe

from app.base.payments.settings import get_payments_settings
from app.core.errors import AppError

STRIPE_HEADER = "Stripe-Signature"
PAYSTACK_HEADER = "x-paystack-signature"
ESCROW_HEADER = "X-Escrow-Signature"

# Stripe's own default: a signed timestamp older than this is a replay and is refused.
STRIPE_TOLERANCE_SECONDS = 300


def _invalid() -> AppError:
    return AppError("invalid_signature", "The webhook signature is missing or invalid.", 400)


def _require_secret(secret: str, provider: str) -> str:
    if not secret:
        raise AppError("webhook_not_configured", f"The {provider} webhook secret is not set.", 503)
    return secret


def _check_hmac(raw_body: bytes, header: str | None, secret: str, digest: str) -> None:
    if not header:
        raise _invalid()
    if not hmac.compare_digest(_sign(raw_body, secret, digest), header.strip().lower()):
        raise _invalid()


def verify_stripe(raw_body: bytes, header: str | None) -> None:
    secret = _require_secret(get_payments_settings().stripe_webhook_secret, "Stripe")
    if not header:
        raise _invalid()
    try:
        stripe.WebhookSignature.verify_header(
            raw_body.decode("utf-8"), header, secret, tolerance=STRIPE_TOLERANCE_SECONDS
        )
    except (stripe.SignatureVerificationError, UnicodeDecodeError) as exc:
        raise _invalid() from exc


def verify_paystack(raw_body: bytes, header: str | None) -> None:
    secret = _require_secret(get_payments_settings().paystack_secret_key, "Paystack")
    _check_hmac(raw_body, header, secret, "sha512")


def verify_escrow(raw_body: bytes, header: str | None) -> None:
    secret = _require_secret(get_payments_settings().escrow_webhook_secret, "escrow")
    _check_hmac(raw_body, header, secret, "sha256")


def _sign(raw_body: bytes, secret: str, digest: str) -> str:
    return hmac.new(secret.encode(), raw_body, digest).hexdigest()


def sign_escrow(raw_body: bytes, secret: str) -> str:
    """The X-Escrow-Signature value for a body (used by the simulated partner and tests)."""
    return _sign(raw_body, secret, "sha256")


def sign_paystack(raw_body: bytes, secret: str) -> str:
    """The x-paystack-signature value for a body (tests and local curl checks)."""
    return _sign(raw_body, secret, "sha512")
