"""Database tables for audit. Inherit from TimestampedBase (gives id, created_at, updated_at).

Owner: Lilian.

Example:

    from sqlalchemy.orm import Mapped, mapped_column
    from app.core.models import TimestampedBase

    class Thing(TimestampedBase):
        __tablename__ = "things"
        name: Mapped[str] = mapped_column()
"""
