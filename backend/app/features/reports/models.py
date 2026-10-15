"""Weekly project reports. Owner: James.

The report agent writes a Markdown draft every Friday; the project's supervisor reviews it; then it is
sent to the client (spec: AI agents, background jobs). One report per project per week.
"""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class ReportStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    SENT = "sent"


class Report(TimestampedBase):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("project_id", "week_start", name="uq_reports_project_week"),
        CheckConstraint(
            "status IN ('draft', 'reviewed', 'sent')",
            name="status_valid",
        ),
        CheckConstraint("extract(isodow from week_start) = 1", name="week_starts_monday"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)  # the Monday of the reported week
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_key: Mapped[str | None] = mapped_column(String(300))  # object-storage key, once rendered
    # The evidence the report cites, so the dashboard can link each claim to its photos.
    evidence_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default="{}"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ReportStatus.DRAFT.value, server_default=ReportStatus.DRAFT.value
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
