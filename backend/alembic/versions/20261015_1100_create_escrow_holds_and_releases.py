"""Create escrow_holds and escrow_releases (day 4: releasing milestone and supplier money).

- escrow_holds (NOT in the spec yet; spec addition): one per funded milestone, keeping the
  partner's hold id that a release has to name.
- escrow_releases (spec table, plus project_id, order_id, hold_id, payee, attempts,
  failure_reason, requested_by): exactly one of milestone_id / order_id; at most one release
  that has not failed per milestone and per order.
- Check constraint names go through op.f(), so the naming convention does not double them.

Owner: Gabriel.

Revision ID: create_escrow_releases
Revises: create_deliveries
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_escrow_releases"
down_revision: str | Sequence[str] | None = "create_deliveries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "escrow_holds",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ref", sa.String(255), nullable=False),
        sa.Column("provider_ref", sa.String(255), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_escrow_holds"),
        sa.UniqueConstraint("milestone_id", name="uq_escrow_holds_milestone_id"),
        sa.UniqueConstraint("ref", name="uq_escrow_holds_ref"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_escrow_holds_project_id_projects"),
        sa.ForeignKeyConstraint(
            ["milestone_id"], ["milestones.id"], name="fk_escrow_holds_milestone_id_milestones"
        ),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_escrow_holds_amount_positive")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_escrow_holds_currency_iso4217")),
        sa.CheckConstraint("status IN ('held', 'pending')", name=op.f("ck_escrow_holds_status_valid")),
    )
    op.create_index("ix_escrow_holds_project_id", "escrow_holds", ["project_id"])

    op.create_table(
        "escrow_releases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hold_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payee", sa.String(100), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("provider_ref", sa.String(255), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_escrow_releases"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="fk_escrow_releases_project_id_projects"
        ),
        sa.ForeignKeyConstraint(
            ["milestone_id"], ["milestones.id"], name="fk_escrow_releases_milestone_id_milestones"
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["material_orders.id"], name="fk_escrow_releases_order_id_material_orders"
        ),
        sa.ForeignKeyConstraint(
            ["hold_id"], ["escrow_holds.id"], name="fk_escrow_releases_hold_id_escrow_holds"
        ),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], name="fk_escrow_releases_requested_by_users"),
        sa.CheckConstraint(
            "(milestone_id IS NULL) <> (order_id IS NULL)", name=op.f("ck_escrow_releases_one_purpose")
        ),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_escrow_releases_amount_positive")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_escrow_releases_currency_iso4217")),
        sa.CheckConstraint(
            "status IN ('requested', 'submitted', 'released', 'failed')",
            name=op.f("ck_escrow_releases_status_valid"),
        ),
    )
    op.create_index("ix_escrow_releases_project_id", "escrow_releases", ["project_id"])
    op.create_index("ix_escrow_releases_milestone_id", "escrow_releases", ["milestone_id"])
    op.create_index("ix_escrow_releases_order_id", "escrow_releases", ["order_id"])
    op.create_index("ix_escrow_releases_hold_id", "escrow_releases", ["hold_id"])
    op.create_index(
        "uq_escrow_releases_open_milestone",
        "escrow_releases",
        ["milestone_id"],
        unique=True,
        postgresql_where=sa.text("milestone_id IS NOT NULL AND status <> 'failed'"),
    )
    op.create_index(
        "uq_escrow_releases_open_order",
        "escrow_releases",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("order_id IS NOT NULL AND status <> 'failed'"),
    )


def downgrade() -> None:
    op.drop_table("escrow_releases")
    op.drop_table("escrow_holds")
