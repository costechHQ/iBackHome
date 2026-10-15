"""Settings for payments, kept here so core/config.py stays Christopher's. Owner: Gabriel.

Read from environment variables (see .env.example):

    LEDGER_APP_ROLE=ibackhome   # database role the API connects as; loses UPDATE/DELETE on ledger_entries
    STRIPE_WEBHOOK_SECRET=      # whsec_... from the Stripe dashboard or `stripe listen`
    PAYSTACK_SECRET_KEY=        # sk_test_...; Paystack signs webhooks with this same key
    ESCROW_WEBHOOK_SECRET=      # shared secret for the escrow partner's webhooks (our scheme until one signs)

A webhook whose secret is empty is refused (503 webhook_not_configured), never accepted unchecked.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class PaymentsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ledger_app_role: str = "ibackhome"

    stripe_webhook_secret: str = ""
    paystack_secret_key: str = ""
    escrow_webhook_secret: str = ""


@lru_cache
def get_payments_settings() -> PaymentsSettings:
    return PaymentsSettings()
