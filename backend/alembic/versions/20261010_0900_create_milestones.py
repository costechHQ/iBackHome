"""Create the milestones table.

Revision ID: create_milestones
Revises: 0001_base
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_milestones"
down_revision: str | Sequence[str] | None = "0001_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

milestone_status = postgresql.ENUM(
    "pending",
    "funded",
    "claimed",
    "verified",
    "approved",
    "disputed",
    "released",
    name="milestone_status",
    create_type=False,
)


def upgrade() -> None:
    milestone_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", milestone_status, server_default="pending", nullable=False),
        sa.Column("funded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="ck_milestones_amount_positive"),
        sa.CheckConstraint("sequence >= 1", name="ck_milestones_sequence_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_milestones"),
        sa.UniqueConstraint("project_id", "sequence", name="uq_milestones_project_id_sequence"),
    )
    op.create_index("ix_milestones_project_id", "milestones", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_milestones_project_id", table_name="milestones")
    op.drop_table("milestones")
    milestone_status.drop(op.get_bind(), checkfirst=True)