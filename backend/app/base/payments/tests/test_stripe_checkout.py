"""The real StripeCheckout class against a mocked Stripe API (respx): no network."""

from urllib.parse import parse_qs

import httpx
import pytest
import respx

from app.base.payments.stripe_checkout import CheckoutRequest, LineItem, StripeCheckout, get_checkout_gateway
from app.core.errors import AppError

SESSIONS_URL = "https://api.stripe.com/v1/checkout/sessions"


def checkout_request(**overrides: object) -> CheckoutRequest:
    fields: dict[str, object] = {
        "currency": "GBP",
        "line_items": [
            LineItem("Duplex: milestone 1, Foundation", 75_000),
            LineItem("iBackHome funding fee", 1_875),
        ],
        "metadata": {"milestone_id": "m-1", "fx_rate": "2000"},
        "success_url": "https://app.example/ok?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": "https://app.example/cancel",
        "client_reference_id": "m-1",
        "idempotency_key": "funding:m-1:abc",
    }
    return CheckoutRequest(**(fields | overrides))  # type: ignore[arg-type]


@respx.mock
async def test_creates_a_session_with_amounts_metadata_and_idempotency_key() -> None:
    route = respx.post(SESSIONS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "cs_test_123",
                "object": "checkout.session",
                "url": "https://checkout.stripe.com/c/pay/cs_test_123",
            },
        )
    )

    session = await StripeCheckout("sk_test_dummy").create_checkout_session(checkout_request())

    assert (session.id, session.url) == ("cs_test_123", "https://checkout.stripe.com/c/pay/cs_test_123")
    sent = route.calls.last.request
    assert sent.headers["Idempotency-Key"] == "funding:m-1:abc"
    assert sent.headers["Authorization"] == "Bearer sk_test_dummy"
    form = parse_qs(sent.content.decode())
    assert form["mode"] == ["payment"]
    assert form["line_items[0][price_data][currency]"] == ["gbp"]
    assert form["line_items[0][price_data][unit_amount]"] == ["75000"]
    assert form["line_items[1][price_data][unit_amount]"] == ["1875"]
    assert form["metadata[fx_rate]"] == ["2000"]
    assert form["payment_intent_data[metadata][milestone_id]"] == ["m-1"]


@respx.mock
async def test_stripe_error_becomes_502() -> None:
    respx.post(SESSIONS_URL).mock(
        return_value=httpx.Response(400, json={"error": {"type": "invalid_request_error", "message": "bad"}})
    )

    with pytest.raises(AppError) as error:
        await StripeCheckout("sk_test_dummy").create_checkout_session(checkout_request())

    assert (error.value.status_code, error.value.code) == (502, "stripe_unavailable")


def test_missing_secret_key_is_503(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.base.payments.settings import get_payments_settings

    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    get_payments_settings.cache_clear()
    try:
        with pytest.raises(AppError) as error:
            get_checkout_gateway()
        assert (error.value.status_code, error.value.code) == (503, "stripe_not_configured")
    finally:
        get_payments_settings.cache_clear()
