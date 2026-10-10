"""Application settings, read from environment variables (see .env.example)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "iBackHome API"
    environment: str = "local"  # local | staging | production
    debug: bool = False

    # Database (async driver: psycopg 3)
    database_url: str = "postgresql+psycopg://ibackhome:ibackhome@localhost:5432/ibackhome"

    # Redis (Celery broker + cache)
    redis_url: str = "redis://localhost:6379/0"

    # Object storage (MinIO locally, S3-compatible in staging/production)
    storage_endpoint: str = "http://localhost:9000"
    storage_bucket: str = "ibackhome-evidence"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"

    # Security (Christopher, day 2)
    jwt_secret: str = "change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 30

    # Comma-separated list of web origins allowed to call the API
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
