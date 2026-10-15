"""Settings for notifications, kept here so core/config.py stays Christopher's. Owner: Lilian.

Read from environment variables (Christopher adds them to .env.example). A channel whose
settings are empty is "not configured": notify() skips it and tries the next one. On
ENVIRONMENT=local an unconfigured channel writes the message to the API log instead.

    NOTIFY_TIMEOUT_SECONDS=10          # per provider call

    EMAIL_SMTP_HOST=                   # e.g. smtp-relay.brevo.com; empty = email not configured
    EMAIL_SMTP_PORT=587
    EMAIL_SMTP_USERNAME=
    EMAIL_SMTP_PASSWORD=
    EMAIL_SMTP_STARTTLS=true
    EMAIL_FROM=                        # e.g. "iBackHome <no-reply@ibackhome.ng>"

    TERMII_API_KEY=                    # SMS; empty = SMS not configured
    TERMII_SENDER_ID=iBackHome         # sender name approved by Termii
    TERMII_BASE_URL=https://api.ng.termii.com

    FCM_PROJECT_ID=                    # Firebase push; empty = push not configured
    FCM_SERVICE_ACCOUNT_JSON=          # the service account key file's contents (one line of JSON)
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotificationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    notify_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_smtp_username: str = ""
    email_smtp_password: str = ""
    email_smtp_starttls: bool = True
    email_from: str = ""

    termii_api_key: str = ""
    termii_sender_id: str = "iBackHome"
    termii_base_url: str = "https://api.ng.termii.com"

    fcm_project_id: str = ""
    fcm_service_account_json: str = ""


@lru_cache
def get_notification_settings() -> NotificationSettings:
    return NotificationSettings()
