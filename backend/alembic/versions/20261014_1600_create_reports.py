"""Create the reports table.

Revision ID: create_reports
Revises: spot_checks_project_fk
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_reports"
down_revision: str | Sequence[str] | None = "spot_checks_project_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column("pdf_key", sa.String(300), nullable=True),
        sa.Column(
            "evidence_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'reviewed', 'sent')", name="ck_reports_status_valid"),
        sa.CheckConstraint("extract(isodow from week_start) = 1", name="ck_reports_week_starts_monday"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_reports_project_id_projects"),
        sa.PrimaryKeyConstraint("id", name="pk_reports"),
        sa.UniqueConstraint("project_id", "week_start", name="uq_reports_project_week"),
    )
    op.create_index("ix_reports_project_id", "reports", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_project_id", table_name="reports")
    op.drop_table("reports")
