"""Test helpers: sign webhook bodies the way each provider does, with test-only secrets."""

import hashlib
import hmac
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from app.base.payments.settings import get_payments_settings
from app.base.payments.signatures import sign_escrow, sign_paystack

# Test-only values, never used outside tests.
STRIPE_SECRET = "whsec_test_only_not_a_real_secret"  # noqa: S105
PAYSTACK_SECRET = "sk_test_only_not_a_real_secret"  # noqa: S105
ESCROW_SECRET = "escrow_test_only_not_a_real_secret"  # noqa: S105


@contextmanager
def webhook_secrets(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Set the three webhook secrets for the duration of a test."""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", STRIPE_SECRET)
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", PAYSTACK_SECRET)
    monkeypatch.setenv("ESCROW_WEBHOOK_SECRET", ESCROW_SECRET)
    get_payments_settings.cache_clear()
    try:
        yield
    finally:
        get_payments_settings.cache_clear()


def body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode()


def stripe_header(raw: bytes, *, secret: str = STRIPE_SECRET, timestamp: int | None = None) -> str:
    """A `Stripe-Signature` header: t=<unix time>,v1=<HMAC-SHA256 of "t.body">."""
    t = int(time.time()) if timestamp is None else timestamp
    signature = hmac.new(secret.encode(), f"{t}.".encode() + raw, hashlib.sha256).hexdigest()
    return f"t={t},v1={signature}"


def stripe_headers(raw: bytes, **kwargs: Any) -> dict[str, str]:
    return {"Stripe-Signature": stripe_header(raw, **kwargs), "Content-Type": "application/json"}


def paystack_headers(raw: bytes, *, secret: str = PAYSTACK_SECRET) -> dict[str, str]:
    return {"x-paystack-signature": sign_paystack(raw, secret), "Content-Type": "application/json"}


def escrow_headers(raw: bytes, *, secret: str = ESCROW_SECRET) -> dict[str, str]:
    return {"X-Escrow-Signature": sign_escrow(raw, secret), "Content-Type": "application/json"}
