"""Milestones and verifications tables.

`milestones.project_id` has no database foreign key yet (the `projects` table came later);
it is a follow-up. A verification is the supervisor's decision on a claimed milestone:
`verified` (with the checklist and the evidence it relies on) or `rejected` (with a reason).
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class MilestoneStatus(enum.StrEnum):
    PENDING = "pending"
    FUNDED = "funded"
    CLAIMED = "claimed"
    VERIFIED = "verified"
    APPROVED = "approved"
    DISPUTED = "disputed"
    RELEASED = "released"


class Milestone(TimestampedBase):
    __tablename__ = "milestones"
    __table_args__ = (
        UniqueConstraint("project_id", "sequence", name="uq_milestones_project_id_sequence"),
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(
            MilestoneStatus,
            name="milestone_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=MilestoneStatus.PENDING,
        server_default=MilestoneStatus.PENDING.value,
    )
    funded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VerificationDecision(enum.StrEnum):
    VERIFIED = "verified"
    REJECTED = "rejected"


class Verification(TimestampedBase):
    __tablename__ = "verifications"
    __table_args__ = (CheckConstraint("decision IN ('verified', 'rejected')", name="decision_valid"),)

    milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id"), index=True, nullable=False
    )
    supervisor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    # [{"item": "...", "passed": true, "evidence_ids": ["<uuid>", ...]}, ...]
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)  # the reason, when rejected
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
