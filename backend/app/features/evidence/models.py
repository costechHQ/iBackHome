"""Evidence tables: registered devices and the photos and videos they capture."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class EvidenceKind(StrEnum):
    PHOTO = "photo"
    VIDEO = "video"


class EvidenceStatus(StrEnum):
    PENDING_CHECKS = "pending_checks"
    ACCEPTED = "accepted"
    FLAGGED = "flagged"
    REJECTED = "rejected"


def _one_of(column: str, values: type[StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(v.value) for v in values)})"


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


class Evidence(TimestampedBase):
    """One photo or video. Server checks (Day 4) move it from pending_checks to accepted/flagged/rejected."""

    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(_one_of("kind", EvidenceKind), name="kind_valid"),
        CheckConstraint(_one_of("status", EvidenceStatus), name="status_valid"),
        CheckConstraint("captured_by_role IN ('supervisor', 'contractor')", name="captured_by_role_valid"),
        CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180", name="coords_valid"
        ),
        CheckConstraint("accuracy_m >= 0", name="accuracy_non_negative"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id"), index=True
    )
    captured_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # The uploader's role at upload time. Contractor evidence is labelled as such and never counts
    # toward a supervisor's verification.
    captured_by_role: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)  # as signed; recomputed in Day 4
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_m: Mapped[float] = mapped_column(Float, nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)  # as signed; checked in Day 4
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    phash: Mapped[int | None] = mapped_column(BigInteger, index=True)  # signed 64-bit, see hashing.py
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=EvidenceStatus.PENDING_CHECKS.value,
        server_default=EvidenceStatus.PENDING_CHECKS.value,
    )
    reject_reason: Mapped[str | None] = mapped_column(Text)
