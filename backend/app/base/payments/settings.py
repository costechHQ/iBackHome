"""Settings for payments, kept here so core/config.py stays Christopher's. Owner: Gabriel.

Read from environment variables (see .env.example):

    LEDGER_APP_ROLE=ibackhome   # database role the API connects as; loses UPDATE/DELETE on ledger_entries
    STRIPE_SECRET_KEY=          # sk_test_...; creates Checkout sessions
    STRIPE_WEBHOOK_SECRET=      # whsec_... from the Stripe dashboard or `stripe listen`
    PAYSTACK_SECRET_KEY=        # sk_test_...; Paystack signs webhooks with this same key
    PAYSTACK_BASE_URL=https://api.paystack.co
    ESCROW_WEBHOOK_SECRET=      # shared secret for the escrow partner's webhooks (our scheme until one signs)

    # FX for test mode: naira per one unit of the client's currency (decimal strings, never floats).
    FX_NGN_PER_GBP=2000
    FX_NGN_PER_USD=1550
    FX_NGN_PER_EUR=1700
    FX_RATES_AS_OF=             # optional ISO 8601 UTC time the rates were taken; empty = "now"

    FUNDING_FEE_BPS=250         # iBackHome's funding fee in basis points (250 = 2.5%)

A webhook whose secret is empty is refused (503 webhook_not_configured), never accepted unchecked.
"""

from datetime import datetime
from decimal import Decimal
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PaymentsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ledger_app_role: str = "ibackhome"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    paystack_secret_key: str = ""
    paystack_base_url: str = "https://api.paystack.co"
    escrow_webhook_secret: str = ""

    fx_ngn_per_gbp: Decimal = Field(default=Decimal("2000"), gt=0)
    fx_ngn_per_usd: Decimal = Field(default=Decimal("1550"), gt=0)
    fx_ngn_per_eur: Decimal = Field(default=Decimal("1700"), gt=0)
    fx_rates_as_of: datetime | None = None

    funding_fee_bps: int = Field(default=250, ge=0, le=10_000)


@lru_cache
def get_payments_settings() -> PaymentsSettings:
    return PaymentsSettings()
