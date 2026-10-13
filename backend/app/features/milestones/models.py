"""Milestones table.

`project_id` has no database foreign key yet because the `projects` table (Christopher)
does not exist on day 1. Add the foreign key in a migration once `projects` lands.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
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
