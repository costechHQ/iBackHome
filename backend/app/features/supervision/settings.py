"""Settings for the public supervisor application form, kept here so core/config.py stays Christopher's.

OPS_NOTIFY_EMAIL=ops@ibackhome.com   # where every new application is emailed (ADR 0005, slice 1)
APPLICATION_LIMIT_PER_IP=5           # applications one IP address may send per window
APPLICATION_LIMIT_WINDOW_MINUTES=60
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SupervisionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ops_notify_email: str = "ops@ibackhome.com"
    application_limit_per_ip: int = 5
    application_limit_window_minutes: int = 60


@lru_cache
def get_supervision_settings() -> SupervisionSettings:
    return SupervisionSettings()
