"""Create payout_recipients and payouts (Paystack NGN payouts).

Not in the spec yet (proposed in Docs/explainers/gabriel/day-03-stripe-funding-and-paystack.md):
- payout_recipients: a user's or supplier's Paystack recipient. The account number is stored
  masked ("******6789"); a check constraint refuses anything else.
- payouts: one row per transfer, unique on our own `reference` so a retry never pays twice.

Owner: Gabriel.

Revision ID: create_payouts
Revises: create_payment_events_escrow
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_payouts"
down_revision: str | Sequence[str] | None = "create_payment_events_escrow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "payout_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("recipient_code", sa.String(64), nullable=False),
        sa.Column("bank_code", sa.String(20), nullable=False),
        sa.Column("bank_name", sa.String(120), nullable=False),
        sa.Column("account_name", sa.String(200), nullable=False),
        sa.Column("account_number_masked", sa.String(10), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_payout_recipients"),
        sa.UniqueConstraint("recipient_code", name="uq_payout_recipients_recipient_code"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_payout_recipients_user_id_users"),
        sa.CheckConstraint("(user_id IS NULL) <> (supplier_id IS NULL)", name="ck_payout_recipients_one_owner"),
        sa.CheckConstraint(
            "account_number_masked ~ '^\\*{6}[0-9]{4}$'", name="ck_payout_recipients_account_number_masked"
        ),
        sa.CheckConstraint("provider IN ('paystack')", name="ck_payout_recipients_provider_valid"),
    )
    op.create_index("ix_payout_recipients_user_id", "payout_recipients", ["user_id"])
    op.create_index("ix_payout_recipients_supplier_id", "payout_recipients", ["supplier_id"])

    op.create_table(
        "payouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(50), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("provider_transfer_code", sa.String(64), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_payouts"),
        sa.UniqueConstraint("reference", name="uq_payouts_reference"),
        sa.ForeignKeyConstraint(
            ["recipient_id"], ["payout_recipients.id"], name="fk_payouts_recipient_id_payout_recipients"
        ),
        sa.CheckConstraint("amount_minor > 0", name="ck_payouts_amount_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'success', 'failed', 'reversed')", name="ck_payouts_status_valid"
        ),
    )
    op.create_index("ix_payouts_recipient_id", "payouts", ["recipient_id"])


def downgrade() -> None:
    op.drop_table("payouts")
    op.drop_table("payout_recipients")
