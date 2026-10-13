"""Create the users, otp_codes and refresh_tokens tables.

Revision ID: create_users_and_auth
Revises: create_price_index
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_users_and_auth"
down_revision: str | Sequence[str] | None = "create_price_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone", sa.String(16), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("full_name", sa.String(120), nullable=True),
        sa.Column("role", sa.String(16), server_default="client", nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("timezone", sa.String(64), server_default="UTC", nullable=False),
        sa.Column("country", sa.String(2), nullable=True),
        *_timestamps(),
        # op.f(): the names are final; without it the naming convention adds "ck_users_" a second time.
        sa.CheckConstraint("phone IS NOT NULL OR email IS NOT NULL", name=op.f("ck_users_phone_or_email")),
        sa.CheckConstraint(
            "role IN ('client', 'contractor', 'supervisor', 'supplier', 'ops')",
            name=op.f("ck_users_role_valid"),
        ),
        sa.CheckConstraint("status IN ('active', 'suspended')", name=op.f("ck_users_status_valid")),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "otp_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier", sa.String(254), nullable=False),
        sa.Column("channel", sa.String(8), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(45), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "channel IN ('sms', 'whatsapp', 'email')", name=op.f("ck_otp_codes_channel_valid")
        ),
        sa.CheckConstraint("attempts >= 0", name=op.f("ck_otp_codes_attempts_not_negative")),
        sa.PrimaryKeyConstraint("id", name="pk_otp_codes"),
    )
    op.create_index("ix_otp_codes_identifier_created_at", "otp_codes", ["identifier", "created_at"])
    op.create_index("ix_otp_codes_requested_ip_created_at", "otp_codes", ["requested_ip", "created_at"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_refresh_tokens_user_id_users"),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"], ["refresh_tokens.id"], name="fk_refresh_tokens_replaced_by_id_refresh_tokens"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_otp_codes_requested_ip_created_at", table_name="otp_codes")
    op.drop_index("ix_otp_codes_identifier_created_at", table_name="otp_codes")
    op.drop_table("otp_codes")
    op.drop_table("users")
