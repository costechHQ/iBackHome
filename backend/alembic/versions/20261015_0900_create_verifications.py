"""Create the verifications table; tidy the milestones check-constraint names.

A verification is the assigned supervisor's decision on a claimed milestone: `verified`
(with the checklist and the photos it relies on) or `rejected` (with the reason in notes).

The two milestones check constraints were created as `ck_milestones_ck_milestones_...`
(the naming convention was applied to an already-prefixed name). They are renamed to
`ck_milestones_...`; nothing else changes.

Revision ID: create_verifications
Revises: create_payouts
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_verifications"
down_revision: str | Sequence[str] | None = "create_payouts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RENAMES = [
    ("ck_milestones_ck_milestones_amount_positive", "ck_milestones_amount_positive"),
    ("ck_milestones_ck_milestones_sequence_positive", "ck_milestones_sequence_positive"),
]


def upgrade() -> None:
    op.create_table(
        "verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supervisor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist", postgresql.JSONB(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('verified', 'rejected')", name=op.f("ck_verifications_decision_valid")
        ),
        sa.ForeignKeyConstraint(
            ["milestone_id"], ["milestones.id"], name=op.f("fk_verifications_milestone_id_milestones")
        ),
        sa.ForeignKeyConstraint(
            ["supervisor_id"], ["users.id"], name=op.f("fk_verifications_supervisor_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verifications")),
    )
    op.create_index(op.f("ix_verifications_milestone_id"), "verifications", ["milestone_id"])
    op.create_index(op.f("ix_verifications_supervisor_id"), "verifications", ["supervisor_id"])

    for old, new in _RENAMES:
        op.execute(f"ALTER TABLE milestones RENAME CONSTRAINT {old} TO {new}")


def downgrade() -> None:
    for old, new in _RENAMES:
        op.execute(f"ALTER TABLE milestones RENAME CONSTRAINT {new} TO {old}")
    op.drop_index(op.f("ix_verifications_supervisor_id"), table_name="verifications")
    op.drop_index(op.f("ix_verifications_milestone_id"), table_name="verifications")
    op.drop_table("verifications")
