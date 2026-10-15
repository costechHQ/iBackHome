"""The notifications table. Owner: Lilian.

One row per notify() call: who it was for, which channel finally carried it (or the last one
tried, if every channel failed), the provider's message id, and why earlier channels failed.
Sends to a raw phone or email (login codes) have no user and never store their data.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class Channel(StrEnum):
    WHATSAPP = "whatsapp"
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"


class NotificationStatus(StrEnum):
    SENT = "sent"
    FAILED = "failed"


# Spec: "falling back WhatsApp -> push -> SMS -> email".
DEFAULT_ORDER: tuple[Channel, ...] = (Channel.WHATSAPP, Channel.PUSH, Channel.SMS, Channel.EMAIL)


class Notification(TimestampedBase):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("channel IN ('whatsapp', 'push', 'sms', 'email')", name="channel_valid"),
        CheckConstraint("status IN ('sent', 'failed')", name="status_valid"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    template: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    recipient: Mapped[str | None] = mapped_column(String(254))  # the phone or email it went to
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    error: Mapped[str | None] = mapped_column(Text)  # why channels failed, e.g. "whatsapp: not configured"
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
