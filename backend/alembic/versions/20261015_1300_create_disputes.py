"""Create disputes (day 5).

Spec columns, plus proposed_outcome / proposed_by / proposed_at (spec addition): the first of
the two ops approvals the spec requires. At most one open dispute per milestone, and the ops
user who resolves must differ from the one who proposed (check constraint).

Owner: Gabriel.

Revision ID: create_disputes
Revises: payout_recipient_supplier_fk
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_disputes"
down_revision: str | Sequence[str] | None = "payout_recipient_supplier_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "disputes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raised_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("proposed_outcome", sa.String(10), nullable=True),
        sa.Column("proposed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.String(4000), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_disputes"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_disputes_project_id_projects"),
        sa.ForeignKeyConstraint(["milestone_id"], ["milestones.id"], name="fk_disputes_milestone_id_milestones"),
        sa.ForeignKeyConstraint(["raised_by"], ["users.id"], name="fk_disputes_raised_by_users"),
        sa.ForeignKeyConstraint(["proposed_by"], ["users.id"], name="fk_disputes_proposed_by_users"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], name="fk_disputes_resolved_by_users"),
        sa.CheckConstraint(
            "status IN ('open', 'resolved_release', 'resolved_reject')", name=op.f("ck_disputes_status_valid")
        ),
        sa.CheckConstraint(
            "proposed_outcome IS NULL OR proposed_outcome IN ('release', 'rework')",
            name=op.f("ck_disputes_proposed_outcome_valid"),
        ),
        sa.CheckConstraint(
            "resolved_by IS NULL OR resolved_by <> proposed_by", name=op.f("ck_disputes_two_ops_users")
        ),
    )
    op.create_index("ix_disputes_project_id", "disputes", ["project_id"])
    op.create_index("ix_disputes_milestone_id", "disputes", ["milestone_id"])
    op.create_index(
        "uq_disputes_open_milestone",
        "disputes",
        ["milestone_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_table("disputes")
