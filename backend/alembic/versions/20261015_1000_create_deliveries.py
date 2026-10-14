"""Create the deliveries table.

Revision ID: create_deliveries
Revises: add_evidence_gps_time
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_deliveries"
down_revision: str | Sequence[str] | None = "add_evidence_gps_time"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantities", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_deliveries"),
        sa.ForeignKeyConstraint(
            ["order_id"], ["material_orders.id"], name="fk_deliveries_order_id_material_orders"
        ),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], name="fk_deliveries_confirmed_by_users"),
        sa.UniqueConstraint("order_id", name="uq_deliveries_order_id"),
    )


def downgrade() -> None:
    op.drop_table("deliveries")
