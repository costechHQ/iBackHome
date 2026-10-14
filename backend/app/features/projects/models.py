"""Tables for projects, their sites and their bill of quantities (BoQ). Owner: Christopher.

Other features read these only through projects/service.py.
A project has exactly one site: the pin and the geofence polygon the evidence checks use.
Its BoQ is a list of priced lines grouped into milestones; client, contractor and ops each approve it.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase

SRID = 4326


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    BOQ_REVIEW = "boq_review"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


def _one_of(column: str, values: type[StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(v.value) for v in values)})"


class Project(TimestampedBase):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(_one_of("status", ProjectStatus), name="status_valid"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
        CheckConstraint("budget_minor > 0", name="budget_positive"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # Empty until the client names a contractor; required before the BoQ is submitted.
    contractor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    supervisor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ProjectStatus.DRAFT.value,
        server_default=ProjectStatus.DRAFT.value,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # ISO 4217, e.g. NGN
    budget_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)


class Site(TimestampedBase):
    __tablename__ = "sites"
    __table_args__ = (Index("ix_sites_geofence", "geofence", postgresql_using="gist"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True
    )
    # Written as EWKT ("SRID=4326;POINT(lon lat)"); read back through service.py, never as raw WKB.
    location: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=SRID, spatial_index=False), nullable=False
    )
    geofence: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=SRID, spatial_index=False), nullable=False
    )


class BoqItem(TimestampedBase):
    """One priced line of the BoQ.

    Lines are grouped into milestones by `milestone_sequence` / `milestone_name` while the BoQ is
    being agreed. `milestone_id` is filled when the BoQ is approved and the milestones are created.
    """

    __tablename__ = "boq_items"
    __table_args__ = (
        UniqueConstraint("project_id", "milestone_sequence", "line_no", name="uq_boq_items_project_id_line"),
        CheckConstraint("milestone_sequence >= 1", name="milestone_sequence_positive"),
        CheckConstraint("line_no >= 1", name="line_no_positive"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price_minor > 0", name="unit_price_positive"),
        CheckConstraint("total_minor > 0", name="total_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id"), index=True
    )
    milestone_sequence: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3... in build order
    milestone_name: Mapped[str] = mapped_column(String(120), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)  # order within the milestone
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. m3, bag, tonne, no.
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # quantity x unit_price_minor, rounded half-up to a whole minor unit (computed by the server).
    total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # the project's currency


class BoqApprovalRole(StrEnum):
    CLIENT = "client"
    CONTRACTOR = "contractor"
    OPS = "ops"


class BoqApproval(TimestampedBase):
    """One of the three approvals of the current BoQ. A new BoQ version clears them."""

    __tablename__ = "boq_approvals"
    __table_args__ = (
        UniqueConstraint("project_id", "role", name="uq_boq_approvals_project_id_role"),
        CheckConstraint(_one_of("role", BoqApprovalRole), name="role_valid"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
