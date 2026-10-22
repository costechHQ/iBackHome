"""Settings for escrow, kept here so core/config.py stays Christopher's. Owner: Gabriel.

ESCROW_PROVIDER=simulated   # which EscrowProvider get_escrow_provider() returns
FUNDING_SUCCESS_URL=http://127.0.0.1:3000/projects/{project_id}/fund/{milestone_id}?session_id={CHECKOUT_SESSION_ID}
FUNDING_CANCEL_URL=http://127.0.0.1:3000/projects/{project_id}/fund/{milestone_id}?cancelled=1

Where Stripe Checkout sends the client back to: the web app's funding page (WEB-CLIENT-007/016), which
shows "waiting for escrow" until the webhook confirms, or "cancelled". The defaults are for local.
We fill in `{project_id}` and `{milestone_id}`; `{CHECKOUT_SESSION_ID}` is passed through
untouched and Stripe fills it in.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class EscrowSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Add the real partner's name here once one signs (spec, open decision 2).
    escrow_provider: Literal["simulated"] = "simulated"

    funding_success_url: str = (
        "http://127.0.0.1:3000/projects/{project_id}/fund/{milestone_id}?session_id={CHECKOUT_SESSION_ID}"
    )
    funding_cancel_url: str = "http://127.0.0.1:3000/projects/{project_id}/fund/{milestone_id}?cancelled=1"


@lru_cache
def get_escrow_settings() -> EscrowSettings:
    return EscrowSettings()
