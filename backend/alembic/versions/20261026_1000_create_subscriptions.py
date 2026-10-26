"""Create subscriptions and subscription_invoices (the monthly supervision fee).

Owner: Christopher.

Revision ID: create_subscriptions
Revises: add_user_consent
Create Date: 2026-10-26 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_subscriptions"
down_revision: str | Sequence[str] | None = "add_user_consent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), server_default="incomplete", nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("past_due_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_by_billing", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stripe_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_subscriptions_project_id_projects"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], name="fk_subscriptions_client_id_users"),
        sa.UniqueConstraint("project_id", name="uq_subscriptions_project_id"),
        sa.UniqueConstraint("stripe_subscription_id", name="uq_subscriptions_stripe_subscription_id"),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_subscriptions_amount_positive")),
        sa.CheckConstraint(
            "currency IN ('GBP', 'USD', 'EUR')", name=op.f("ck_subscriptions_currency_supported")
        ),
        sa.CheckConstraint(
            "status IN ('incomplete', 'active', 'past_due', 'canceled')",
            name=op.f("ck_subscriptions_status_valid"),
        ),
    )
    op.create_index("ix_subscriptions_client_id", "subscriptions", ["client_id"])
    op.create_table(
        "subscription_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_invoice_id", sa.String(255), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_subscription_invoices"),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            name="fk_subscription_invoices_subscription_id_subscriptions",
        ),
        sa.UniqueConstraint("stripe_invoice_id", name="uq_subscription_invoices_stripe_invoice_id"),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_subscription_invoices_amount_positive")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_subscription_invoices_currency_iso4217")),
    )
    op.create_index("ix_subscription_invoices_subscription_id", "subscription_invoices", ["subscription_id"])


def downgrade() -> None:
    op.drop_table("subscription_invoices")
    op.drop_table("subscriptions")
