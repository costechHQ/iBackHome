"""Tables for projects and their sites. Owner: Christopher.

Other features read these only through projects/service.py.
A project has exactly one site: the pin and the geofence polygon the evidence checks use.
"""

import uuid
from enum import StrEnum
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
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
