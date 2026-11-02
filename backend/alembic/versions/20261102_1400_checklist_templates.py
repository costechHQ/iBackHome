"""Checklist templates, and the checklist copied into each milestone.

checklist_templates: ops' list of what to check for a kind of milestone, found by the milestone's name.
milestones.checklist: that list, copied when the milestone is created (NULL on older milestones, which read
as the generic default). No template content is seeded: the wording is ops'.

Revision ID: checklist_templates
Revises: supervisor_nin
Create Date: 2026-11-02 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "checklist_templates"
down_revision: str | Sequence[str] | None = "supervisor_nin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checklist_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_key", sa.String(length=120), nullable=False),
        sa.Column("milestone_name", sa.String(length=120), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_checklist_templates"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_checklist_templates_updated_by_users"),
        sa.UniqueConstraint("milestone_key", name="uq_checklist_templates_milestone_key"),
    )
    op.add_column("milestones", sa.Column("checklist", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("milestones", "checklist")
    op.drop_table("checklist_templates")
