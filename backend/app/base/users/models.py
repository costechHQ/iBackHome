"""Database tables for users: accounts, one-time login codes and refresh tokens. Owner: Christopher.

Other modules use these through service.py; they never query these tables directly.
Secrets are never stored: OTP codes are kept as an HMAC-SHA256, refresh tokens as a SHA-256.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class Role(StrEnum):
    CLIENT = "client"
    CONTRACTOR = "contractor"
    SUPERVISOR = "supervisor"
    SUPPLIER = "supplier"
    OPS = "ops"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class OtpChannel(StrEnum):
    SMS = "sms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"


def _one_of(column: str, values: type[StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(v.value) for v in values)})"


class User(TimestampedBase):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("phone IS NOT NULL OR email IS NOT NULL", name="phone_or_email"),
        CheckConstraint(_one_of("role", Role), name="role_valid"),
        CheckConstraint(_one_of("status", UserStatus), name="status_valid"),
    )

    phone: Mapped[str | None] = mapped_column(String(16), unique=True)  # E.164, e.g. +2348031234567
    email: Mapped[str | None] = mapped_column(String(254), unique=True)  # stored lower-case
    full_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default=Role.CLIENT.value, server_default=Role.CLIENT.value
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=UserStatus.ACTIVE.value, server_default=UserStatus.ACTIVE.value
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC", server_default="UTC")
    country: Mapped[str | None] = mapped_column(String(2))  # ISO 3166-1 alpha-2


class OtpCode(TimestampedBase):
    """One login challenge. Only the newest unconsumed code for an identifier can be used."""

    __tablename__ = "otp_codes"
    __table_args__ = (
        CheckConstraint(_one_of("channel", OtpChannel), name="channel_valid"),
        CheckConstraint("attempts >= 0", name="attempts_not_negative"),
        # Rate limits count recent rows per identifier and per IP.
        Index("ix_otp_codes_identifier_created_at", "identifier", "created_at"),
        Index("ix_otp_codes_requested_ip_created_at", "requested_ip", "created_at"),
    )

    identifier: Mapped[str] = mapped_column(String(254), nullable=False)  # normalised phone or email
    channel: Mapped[str] = mapped_column(String(8), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # hex HMAC-SHA256, never the code
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Set when the code is used, or replaced by a newer one; either way it can't be used again.
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_ip: Mapped[str] = mapped_column(String(45), nullable=False)  # fits IPv6


class RefreshToken(TimestampedBase):
    """A 30-day refresh token. Rotated on use: each one can be exchanged exactly once."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # hex SHA-256
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id")
    )
