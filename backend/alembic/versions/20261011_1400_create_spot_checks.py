"""Create the spot_checks table.

Revision ID: create_spot_checks
Revises: create_supervisor_profiles
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_spot_checks"
down_revision: str | Sequence[str] | None = "create_supervisor_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spot_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supervisor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["supervisor_id"], ["users.id"], name="fk_spot_checks_supervisor_id_users"),
        sa.ForeignKeyConstraint(["scheduled_by"], ["users.id"], name="fk_spot_checks_scheduled_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_spot_checks"),
    )
    op.create_index("ix_spot_checks_project_id", "spot_checks", ["project_id"])
    op.create_index("ix_spot_checks_supervisor_id", "spot_checks", ["supervisor_id"])


def downgrade() -> None:
    op.drop_index("ix_spot_checks_supervisor_id", table_name="spot_checks")
    op.drop_index("ix_spot_checks_project_id", table_name="spot_checks")
    op.drop_table("spot_checks")
