"""Application settings, read from environment variables (see .env.example)."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_LENGTH = 32
_PLACEHOLDER_SECRETS = {"change-me", "change-me-to-a-long-random-string"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "iBackHome API"
    environment: str = "local"  # local | staging | production
    debug: bool = False

    # Database (async driver: psycopg 3)
    database_url: str = "postgresql+psycopg://ibackhome:ibackhome@localhost:5432/ibackhome"

    # Redis (Celery broker + cache)
    redis_url: str = "redis://localhost:6379/0"

    # Object storage (SeaweedFS locally via docker compose, S3-compatible R2/B2 in staging/production)
    storage_endpoint: str = "http://localhost:9000"
    storage_bucket: str = "ibackhome-evidence"
    storage_access_key: str = "ibackhome"
    storage_secret_key: str = "ibackhome-dev-secret"

    # Security (Christopher, day 2)
    jwt_secret: str = "change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 30

    # One-time login codes (spec: 6 digits, valid 5 minutes, max 5 attempts, rate-limited per phone and IP)
    otp_ttl_minutes: int = 5
    otp_max_attempts: int = 5
    otp_limit_per_identifier: int = 3
    otp_limit_per_ip: int = 10
    otp_limit_window_minutes: int = 15

    # Comma-separated list of web origins allowed to call the API
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _real_secret_outside_local(self) -> "Settings":
        """Refuse to start staging or production with a placeholder JWT secret."""
        if self.environment != "local" and (
            self.jwt_secret in _PLACEHOLDER_SECRETS or len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH
        ):
            raise ValueError(
                f"JWT_SECRET must be a random value of at least {MIN_JWT_SECRET_LENGTH} characters "
                f"when ENVIRONMENT={self.environment}."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
