"""Settings for the website assistant (ADR 0006), kept here so core/config.py stays Christopher's.

ASSISTANT_ENABLED=false             # off until switched on; answers 503 assistant_unavailable while off
ASSISTANT_LIMIT_PER_IP=10           # questions one IP address may ask per window
ASSISTANT_LIMIT_WINDOW_MINUTES=10
ASSISTANT_DAILY_CAP=2000            # answers in total per day (UTC); over it, 503 assistant_busy
ASSISTANT_CONTACT_EMAIL=hello@ibackhome.com
ASSISTANT_CONTACT_WHATSAPP=+234 803 836 2327
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AssistantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    assistant_enabled: bool = False
    assistant_limit_per_ip: int = 10
    assistant_limit_window_minutes: int = 10
    assistant_daily_cap: int = 2000
    # What the answers say when they point a visitor to a person. Same values as the website's contact page.
    assistant_contact_email: str = "hello@ibackhome.com"
    assistant_contact_whatsapp: str = "+234 803 836 2327"


@lru_cache
def get_assistant_settings() -> AssistantSettings:
    return AssistantSettings()
