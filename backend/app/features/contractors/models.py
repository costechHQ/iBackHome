"""Contractor applications and profiles (ADR 0007, phase 1). Owner: Christopher.

An application comes from the public form on /contractors and has no user yet. Ops vet it; approving it
creates the contractor's user (through users.invite_contractor) and a `contractor_profiles` row, the
directory that ops shortlist from in phase 2. There is no NIN here: ops check registration and references
first.

Columns holding a phone number, an email address or an IP address are left out of the audit log
(`info={"audit": False}`): the log is append-only, so personal contact details could never be removed from it.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase

SPECIALTIES = ("buildings", "roofing", "finishing", "civil_works", "other")


class ContractorApplicationStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProfileStatus(enum.StrEnum):
    APPROVED = "approved"
    SUSPENDED = "suspended"


class ContractorApplication(TimestampedBase):
    __tablename__ = "contractor_applications"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="status_valid"),
        CheckConstraint("years_in_business BETWEEN 0 AND 80", name="years_in_business_range"),
        CheckConstraint("projects_completed BETWEEN 0 AND 10000", name="projects_completed_range"),
        # One pending application per phone and per email; the service checks first for a clear 409.
        Index(
            "uq_contractor_applications_pending_phone",
            "phone",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "uq_contractor_applications_pending_email",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_contractor_applications_requested_ip_created_at", "requested_ip", "created_at"),
        Index("ix_contractor_applications_status_created_at", "status", "created_at"),
    )

    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False, info={"audit": False})  # E.164
    email: Mapped[str] = mapped_column(String(254), nullable=False, info={"audit": False})  # lower-case
    states_served: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    specialties: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    years_in_business: Mapped[int] = mapped_column(Integer, nullable=False)
    projects_completed: Mapped[int] = mapped_column(Integer, nullable=False)  # declared by the applicant
    cac_rc_number: Mapped[str | None] = mapped_column(String(30))
    corbon_number: Mapped[str | None] = mapped_column(String(40))
    reference_1_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reference_1_phone: Mapped[str] = mapped_column(String(16), nullable=False, info={"audit": False})
    reference_2_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reference_2_phone: Mapped[str] = mapped_column(String(16), nullable=False, info={"audit": False})

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ContractorApplicationStatus.PENDING.value,
        server_default="pending",
    )
    # Ticked by ops while vetting. Approval needs both references, and the registration when a CAC or
    # CORBON number was given.
    registration_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reference_1_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reference_2_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    ops_notes: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_ip: Mapped[str] = mapped_column(String(45), nullable=False, info={"audit": False})
    # Set when each email went out, so a retried job never sends one twice.
    ops_emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    receipt_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContractorProfile(TimestampedBase):
    """An approved contractor: what ops may offer to clients in phase 2. Created on approval."""

    __tablename__ = "contractor_profiles"
    __table_args__ = (
        CheckConstraint("vetting_status IN ('approved', 'suspended')", name="vetting_status_valid"),
        Index("ix_contractor_profiles_listed_vetting_status", "listed", "vetting_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contractor_applications.id")
    )
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)  # written by ops from the application
    states_served: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    specialties: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    years_in_business: Mapped[int] = mapped_column(Integer, nullable=False)
    projects_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    vetting_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProfileStatus.APPROVED.value, server_default="approved"
    )
    vetted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vetted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    listed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
