"""Settings for subscriptions, kept here so core/config.py stays Christopher's.

SUBSCRIPTION_REQUIRED=true   # the final BoQ approval needs an active subscription (false: staging demos)
SUBSCRIPTION_PRICE_GBP_MINOR=4900   # monthly price per project, in pence / cents (placeholders until the
SUBSCRIPTION_PRICE_USD_MINOR=5900   # price is agreed; PRD "figure to collect in week one")
SUBSCRIPTION_PRICE_EUR_MINOR=5500
SUBSCRIPTION_SUCCESS_URL=http://127.0.0.1:3000/projects/{project_id}/subscription?session_id={CHECKOUT_SESSION_ID}
SUBSCRIPTION_CANCEL_URL=http://127.0.0.1:3000/projects/{project_id}/subscription?cancelled=1

We fill in `{project_id}`; `{CHECKOUT_SESSION_ID}` is passed through untouched and Stripe fills it in.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SubscriptionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    subscription_required: bool = True
    subscription_price_gbp_minor: int = Field(default=4900, gt=0)
    subscription_price_usd_minor: int = Field(default=5900, gt=0)
    subscription_price_eur_minor: int = Field(default=5500, gt=0)
    subscription_success_url: str = (
        "http://127.0.0.1:3000/projects/{project_id}/subscription?session_id={CHECKOUT_SESSION_ID}"
    )
    subscription_cancel_url: str = "http://127.0.0.1:3000/projects/{project_id}/subscription?cancelled=1"

    def price_minor(self, currency: str) -> int:
        return {
            "GBP": self.subscription_price_gbp_minor,
            "USD": self.subscription_price_usd_minor,
            "EUR": self.subscription_price_eur_minor,
        }[currency]


@lru_cache
def get_subscription_settings() -> SubscriptionSettings:
    return SubscriptionSettings()
