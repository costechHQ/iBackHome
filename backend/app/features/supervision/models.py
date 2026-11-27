"""Supervisor vetting and spot-check tables. Owner: James.

People columns point at `users` and `spot_checks.project_id` at `projects` (both Christopher's tables).

A supervisor can only be assigned once ops has passed all four checks (PRD FR-02):
professional registration, NIN, and both guarantors.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class VettingStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SupervisorProfile(TimestampedBase):
    __tablename__ = "supervisor_profiles"
    __table_args__ = (CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating_range"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    registration_body: Mapped[str] = mapped_column(String(120), nullable=False)  # e.g. COREN, NIOB
    registration_no: Mapped[str] = mapped_column(String(60), nullable=False)
    guarantor_1: Mapped[str] = mapped_column(String(200), nullable=False)  # name and phone
    guarantor_2: Mapped[str] = mapped_column(String(200), nullable=False)

    # The NIN (11 digits). The full number is kept encrypted only while the application is pending, for ops to
    # check, and is wiped when they decide; the last 4 digits stay. `audit: False` keeps the ciphertext out of
    # the append-only audit log, where a later wipe could never reach it. See nin.py.
    nin_encrypted: Mapped[str | None] = mapped_column(Text, info={"audit": False})
    nin_last4: Mapped[str | None] = mapped_column(String(4))

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
    vetted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
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

    supervisor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    contractor_phone: Mapped[str] = mapped_column(String(16), nullable=False)  # E.164, like users.phone
    relationship: Mapped[str] = mapped_column(String(60), nullable=False)


class SpotCheck(TimestampedBase):
    """An unannounced visit scheduled by ops. Never shown to the contractor (PRD FR-11)."""

    __tablename__ = "spot_checks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    supervisor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    scheduled_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    findings: Mapped[str | None] = mapped_column(Text)


class WebApplicationStatus(enum.StrEnum):
    PENDING = "pending"


class SupervisorWebApplication(TimestampedBase):
    """An application from the public form on /supervisors (ADR 0005, slice 1). The applicant has no user yet.

    There is no NIN here, on purpose: ops check the registration number first, and only then ask for the NIN
    (the identity lookup costs money). Rows are kept 12 months after a rejection, then deleted (proposed).
    """

    __tablename__ = "supervisor_applications"
    __table_args__ = (
        CheckConstraint("status IN ('pending')", name="status_valid"),
        CheckConstraint(
            "registration_body IN ('COREN', 'NIOB', 'CORBON', 'other')", name="registration_body_valid"
        ),
        CheckConstraint("years_experience BETWEEN 0 AND 60", name="years_experience_range"),
        # One pending application per phone and per email; the service checks first for a clear 409.
        Index(
            "uq_supervisor_applications_pending_phone",
            "phone",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "uq_supervisor_applications_pending_email",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_supervisor_applications_requested_ip_created_at", "requested_ip", "created_at"),
    )

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)  # E.164
    email: Mapped[str] = mapped_column(String(254), nullable=False)  # lower-case
    state: Mapped[str] = mapped_column(String(60), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    registration_body: Mapped[str] = mapped_column(String(20), nullable=False)
    registration_no: Mapped[str] = mapped_column(String(60), nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False)
    guarantor_1_name: Mapped[str] = mapped_column(String(200), nullable=False)
    guarantor_1_phone: Mapped[str] = mapped_column(String(16), nullable=False)
    guarantor_2_name: Mapped[str] = mapped_column(String(200), nullable=False)
    guarantor_2_phone: Mapped[str] = mapped_column(String(16), nullable=False)
    # Declared relatives who are contractors: [{"name": ..., "phone": "+234..."}]. May be empty.
    relatives: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WebApplicationStatus.PENDING.value, server_default="pending"
    )
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_ip: Mapped[str] = mapped_column(String(45), nullable=False)  # fits IPv6
    # Set when each email went out, so a retried job never sends one twice.
    ops_emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    receipt_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
