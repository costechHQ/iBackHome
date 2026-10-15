"""Settings for notifications, kept here so core/config.py stays Christopher's. 

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

    WHATSAPP_ACCESS_TOKEN=             # WhatsApp Business Cloud API; empty = WhatsApp not configured
    WHATSAPP_PHONE_NUMBER_ID=          # the sending number's ID from Meta's WhatsApp Manager
    WHATSAPP_API_VERSION=v23.0
    WHATSAPP_BASE_URL=https://graph.facebook.com
    WHATSAPP_LANGUAGE=en               # language code the templates were approved in
    WHATSAPP_USE_TEMPLATES=true        # false = always plain text (only for test numbers that wrote first)

    NOTIFY_RETRY_HOURS=24              # notifications.retry_failed gives up on rows older than this
    NOTIFY_MAX_ATTEMPTS=20             # ...or once this many channel tries have failed
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

    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v23.0"
    whatsapp_base_url: str = "https://graph.facebook.com"
    whatsapp_language: str = "en"
    whatsapp_use_templates: bool = True

    notify_retry_hours: int = Field(default=24, ge=1, le=168)
    notify_max_attempts: int = Field(default=20, ge=1, le=100)


@lru_cache
def get_notification_settings() -> NotificationSettings:
    return NotificationSettings()
