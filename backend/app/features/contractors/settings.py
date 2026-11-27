"""Settings for the contractor application form, kept here so core/config.py stays Christopher's.

OPS_NOTIFY_EMAIL=ops@ibackhome.com   # where each new application is emailed (shared with the supervisor form)
CONTRACTOR_APPLICATION_LIMIT_PER_IP=5              # applications one IP address may send per window
CONTRACTOR_APPLICATION_LIMIT_WINDOW_MINUTES=60
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ContractorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ops_notify_email: str = "ops@ibackhome.com"
    contractor_application_limit_per_ip: int = 5
    contractor_application_limit_window_minutes: int = 60


@lru_cache
def get_contractor_settings() -> ContractorSettings:
    return ContractorSettings()
