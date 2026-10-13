"""Create the price_index_entries table.

Revision ID: create_price_index
Revises: create_milestones
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_price_index"
down_revision: str | Sequence[str] | None = "create_milestones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "price_index_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_key", sa.String(80), nullable=False),
        sa.Column("item", sa.String(120), nullable=False),
        sa.Column("unit", sa.String(60), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), server_default="NGN", nullable=False),
        sa.Column("supplier_name", sa.String(120), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("source", sa.String(60), server_default="survey", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price_minor > 0", name="ck_price_index_entries_price_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_price_index_entries"),
        sa.UniqueConstraint(
            "item_key", "supplier_name", "observed_on", name="uq_price_index_entries_observation"
        ),
    )
    op.create_index("ix_price_index_entries_item_key", "price_index_entries", ["item_key"])


def downgrade() -> None:
    op.drop_index("ix_price_index_entries_item_key", table_name="price_index_entries")
    op.drop_table("price_index_entries")