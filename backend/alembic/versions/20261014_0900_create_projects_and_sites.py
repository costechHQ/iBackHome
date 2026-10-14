"""Create the projects and sites tables.

A project has one site: a pin (POINT) and a geofence (POLYGON), both SRID 4326, with a GiST index
on the geofence (spec: "Indexes that matter").

Revision ID: create_projects_and_sites
Revises: create_audit_log
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "create_projects_and_sites"
down_revision: str | Sequence[str] | None = "create_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supervisor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("budget_minor", sa.BigInteger(), nullable=False),
        *_timestamps(),
        # op.f(): the names are final; without it the naming convention adds "ck_projects_" a second time.
        sa.CheckConstraint(
            "status IN ('draft', 'boq_review', 'active', 'paused', 'completed')",
            name=op.f("ck_projects_status_valid"),
        ),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_projects_currency_iso4217")),
        sa.CheckConstraint("budget_minor > 0", name=op.f("ck_projects_budget_positive")),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], name="fk_projects_client_id_users"),
        sa.ForeignKeyConstraint(["contractor_id"], ["users.id"], name="fk_projects_contractor_id_users"),
        sa.ForeignKeyConstraint(["supervisor_id"], ["users.id"], name="fk_projects_supervisor_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
    )
    op.create_index("ix_projects_client_id", "projects", ["client_id"])
    op.create_index("ix_projects_contractor_id", "projects", ["contractor_id"])
    op.create_index("ix_projects_supervisor_id", "projects", ["supervisor_id"])

    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "location", Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
        ),
        sa.Column(
            "geofence", Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_sites_project_id_projects"),
        sa.PrimaryKeyConstraint("id", name="pk_sites"),
        sa.UniqueConstraint("project_id", name="uq_sites_project_id"),
    )
    op.create_index("ix_sites_geofence", "sites", ["geofence"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_sites_geofence", table_name="sites", postgresql_using="gist")
    op.drop_table("sites")
    op.drop_index("ix_projects_supervisor_id", table_name="projects")
    op.drop_index("ix_projects_contractor_id", table_name="projects")
    op.drop_index("ix_projects_client_id", table_name="projects")
    op.drop_table("projects")
