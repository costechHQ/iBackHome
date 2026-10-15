"""Create the agent_runs table.

Revision ID: create_agent_runs
Revises: create_reports
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_agent_runs"
down_revision: str | Sequence[str] | None = "create_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent", sa.String(60), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input", postgresql.JSONB(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('succeeded', 'failed')", name="ck_agent_runs_status_valid"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_agent_runs_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runs"),
    )
    op.create_index("ix_agent_runs_agent", "agent_runs", ["agent"])


def downgrade() -> None:
    op.drop_index("ix_agent_runs_agent", table_name="agent_runs")
    op.drop_table("agent_runs")
