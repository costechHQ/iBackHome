"""Supervisor vetting and spot-check tables. Owner: James.

User and project columns have no database foreign key yet because the `users` and `projects`
tables (Christopher) don't exist yet. Add the foreign keys in a migration once they land.

A supervisor can only be assigned once ops has passed all four checks (PRD FR-02):
professional registration, NIN, and both guarantors.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class VettingStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SupervisorProfile(TimestampedBase):
    __tablename__ = "supervisor_profiles"
    __table_args__ = (CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating_range"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    registration_body: Mapped[str] = mapped_column(String(120), nullable=False)  # e.g. COREN, NIOB
    registration_no: Mapped[str] = mapped_column(String(60), nullable=False)
    guarantor_1: Mapped[str] = mapped_column(String(200), nullable=False)  # name and phone
    guarantor_2: Mapped[str] = mapped_column(String(200), nullable=False)

    # Ticked by ops during vetting; approval needs all four.
    registration_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    nin_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    guarantor_1_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    guarantor_2_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    vetting_status: Mapped[VettingStatus] = mapped_column(
        Enum(VettingStatus, name="vetting_status", values_callable=lambda e: [m.value for m in e]),
        default=VettingStatus.PENDING,
        server_default=VettingStatus.PENDING.value,
        nullable=False,
    )
    vetted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    vetted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))


class SupervisorRelation(TimestampedBase):
    """A contractor the supervisor declared as related at vetting; they are never paired on a project.

    Stored by phone because contractors are invited by phone and may not have an account yet.
    """

    __tablename__ = "supervisor_relations"
    __table_args__ = (
        UniqueConstraint(
            "supervisor_id", "contractor_phone", name="uq_supervisor_relations_supervisor_phone"
        ),
    )

    supervisor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    contractor_phone: Mapped[str] = mapped_column(String(20), nullable=False)  # E.164, e.g. +2348012345678
    relationship: Mapped[str] = mapped_column(String(60), nullable=False)


class SpotCheck(TimestampedBase):
    """An unannounced visit scheduled by ops. Never shown to the contractor (PRD FR-11)."""

    __tablename__ = "spot_checks"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    supervisor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    scheduled_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    findings: Mapped[str | None] = mapped_column(Text)
