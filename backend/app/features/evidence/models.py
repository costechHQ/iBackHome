"""Evidence tables."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class Device(TimestampedBase):
    __tablename__ = "devices"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    device_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)  # base64 X.509 SPKI DER, P-256
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
