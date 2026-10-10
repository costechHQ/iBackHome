"""Imports every `models.py` so Alembic and the app see all tables. Nobody edits this file."""

from sqlalchemy import MetaData

from app.core import idempotency  # noqa: F401  (core table: idempotency_keys)
from app.core.discovery import import_all
from app.core.models import Base


def load_all_models() -> MetaData:
    import_all("models")
    return Base.metadata
