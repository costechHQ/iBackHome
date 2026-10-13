"""Create the devices table.

Revision ID: create_devices
Revises: create_users_and_auth
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_devices"
down_revision: str | Sequence[str] | None = "create_users_and_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(128), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_devices"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_devices_user_id_users"),
        sa.UniqueConstraint("device_id", name="uq_devices_device_id"),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_devices_user_id", table_name="devices")
    op.drop_table("devices")
