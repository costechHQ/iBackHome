"""The notifications table.

One row per notify() call: who it was for, which channel finally carried it (or the last one
tried, if every channel failed), the provider's message id, and why earlier channels failed.
Sends to a raw phone or email (login codes) have no user and never store their data.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
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
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # set by the in-app feed


class PushToken(TimestampedBase):
    """One signed-in app install's Firebase token, so push can reach that phone.

    `device_pk` is the evidence device's id (devices.id). There is no foreign key: notifications is a base
    module and must not depend on a feature's table. The evidence service checks the device belongs to the
    caller before saving a token and forgets it when the device is revoked. One token per device; a token
    that moves to another user (someone else signed in on that phone) replaces the old row.
    """

    __tablename__ = "push_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    device_pk: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    token: Mapped[str] = mapped_column(Text, index=True, nullable=False)


class NotificationPreference(TimestampedBase):
    """A person's push settings (design: AND-SUPERVISOR-015). No row means the defaults: push on, previews on.

    Spot-check SMS is not here: it cannot be turned off.
    """

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    # True: a lock screen shows only "You have a new update from iBackHome", never the message text.
    hide_previews: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
