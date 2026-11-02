"""Create push_tokens and notification_preferences, so push can reach a person's phone.

push_tokens: one Firebase token per app install (the evidence device's id). notification_preferences:
the two settings in the design (push on or off, hide previews on the lock screen); no row means the defaults.

Revision ID: create_push_tokens
Revises: notifications_read_at
Create Date: 2026-11-02 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_push_tokens"
down_revision: str | Sequence[str] | None = "notifications_read_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "push_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_pk", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_push_tokens"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_push_tokens_user_id_users"),
        sa.UniqueConstraint("device_pk", name="uq_push_tokens_device_pk"),
    )
    op.create_index("ix_push_tokens_user_id", "push_tokens", ["user_id"])
    op.create_index("ix_push_tokens_token", "push_tokens", ["token"])

    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("push_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("hide_previews", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_notification_preferences"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notification_preferences_user_id_users"
        ),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_index("ix_push_tokens_token", table_name="push_tokens")
    op.drop_index("ix_push_tokens_user_id", table_name="push_tokens")
    op.drop_table("push_tokens")
