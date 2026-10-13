"""Settings for payments, kept here so core/config.py stays Christopher's. Owner: Gabriel.

Read from environment variables (see .env.example):

    LEDGER_APP_ROLE=ibackhome   # database role the API connects as; loses UPDATE/DELETE on ledger_entries
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class PaymentsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ledger_app_role: str = "ibackhome"


@lru_cache
def get_payments_settings() -> PaymentsSettings:
    return PaymentsSettings()
