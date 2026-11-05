"""Settings for subscriptions, kept here so core/config.py stays Christopher's.

SUBSCRIPTION_REQUIRED=true   # the final BoQ approval needs an active subscription (false: staging demos)
SUBSCRIPTION_PRICE_BASIC_MINOR=10000      # monthly price per project in US cents: Basic $100 (2 visits),
SUBSCRIPTION_PRICE_STANDARD_MINOR=15000   # Standard $150 (3 visits), Premium $200 (4 visits).
SUBSCRIPTION_PRICE_PREMIUM_MINOR=20000    # Clients pay in USD only; see plans.py.
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
    subscription_price_basic_minor: int = Field(default=10_000, gt=0)
    subscription_price_standard_minor: int = Field(default=15_000, gt=0)
    subscription_price_premium_minor: int = Field(default=20_000, gt=0)
    subscription_success_url: str = (
        "http://127.0.0.1:3000/projects/{project_id}/subscription?session_id={CHECKOUT_SESSION_ID}"
    )
    subscription_cancel_url: str = "http://127.0.0.1:3000/projects/{project_id}/subscription?cancelled=1"

    def plan_price_minor(self, plan: str) -> int:
        return {
            "basic": self.subscription_price_basic_minor,
            "standard": self.subscription_price_standard_minor,
            "premium": self.subscription_price_premium_minor,
        }[plan]


@lru_cache
def get_subscription_settings() -> SubscriptionSettings:
    return SubscriptionSettings()
