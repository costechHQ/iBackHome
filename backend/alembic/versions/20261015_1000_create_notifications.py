"""Create the notifications table.

One row per notify() / notify_address() call: who it was for, the channel that carried it (or
the last one tried), the provider's message id, and why earlier channels failed.

Revision ID: create_notifications
Revises: create_payouts
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_notifications"
down_revision: str | Sequence[str] | None = "create_payouts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("template", sa.String(80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("recipient", sa.String(254), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider_ref", sa.String(255), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="1", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "channel IN ('whatsapp', 'push', 'sms', 'email')", name=op.f("ck_notifications_channel_valid")
        ),
        sa.CheckConstraint("status IN ('sent', 'failed')", name=op.f("ck_notifications_status_valid")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_notifications_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"])
    op.create_index(op.f("ix_notifications_status"), "notifications", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_status"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
