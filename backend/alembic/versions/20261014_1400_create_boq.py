"""Create the boq_items and boq_approvals tables.

BoQ lines are grouped into milestones by milestone_sequence / milestone_name until the BoQ is
approved; then milestone_id points at the milestone created for that group.

Revision ID: create_boq
Revises: create_projects_and_sites
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_boq"
down_revision: str | Sequence[str] | None = "create_projects_and_sites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "boq_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("milestone_sequence", sa.Integer(), nullable=False),
        sa.Column("milestone_name", sa.String(120), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("total_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        *_timestamps(),
        # op.f(): the names are final; without it the naming convention adds "ck_boq_items_" a second time.
        sa.CheckConstraint("milestone_sequence >= 1", name=op.f("ck_boq_items_milestone_sequence_positive")),
        sa.CheckConstraint("line_no >= 1", name=op.f("ck_boq_items_line_no_positive")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_boq_items_quantity_positive")),
        sa.CheckConstraint("unit_price_minor > 0", name=op.f("ck_boq_items_unit_price_positive")),
        sa.CheckConstraint("total_minor > 0", name=op.f("ck_boq_items_total_positive")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_boq_items_currency_iso4217")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_boq_items_project_id_projects"),
        sa.ForeignKeyConstraint(["milestone_id"], ["milestones.id"], name="fk_boq_items_milestone_id_milestones"),
        sa.PrimaryKeyConstraint("id", name="pk_boq_items"),
        sa.UniqueConstraint("project_id", "milestone_sequence", "line_no", name="uq_boq_items_project_id_line"),
    )
    op.create_index("ix_boq_items_project_id", "boq_items", ["project_id"])
    op.create_index("ix_boq_items_milestone_id", "boq_items", ["milestone_id"])

    op.create_table(
        "boq_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("role IN ('client', 'contractor', 'ops')", name=op.f("ck_boq_approvals_role_valid")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_boq_approvals_project_id_projects"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_boq_approvals_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_boq_approvals"),
        sa.UniqueConstraint("project_id", "role", name="uq_boq_approvals_project_id_role"),
    )
    op.create_index("ix_boq_approvals_project_id", "boq_approvals", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_boq_approvals_project_id", table_name="boq_approvals")
    op.drop_table("boq_approvals")
    op.drop_index("ix_boq_items_milestone_id", table_name="boq_items")
    op.drop_index("ix_boq_items_project_id", table_name="boq_items")
    op.drop_table("boq_items")
