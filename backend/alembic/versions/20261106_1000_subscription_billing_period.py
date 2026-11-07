"""Subscription billing period: monthly, biannual (5 months paid for 6) or annual (10 paid for 12).

Existing rows become `monthly`; their stored price is already the monthly price.

Revision ID: subscription_billing_period
Revises: subscription_plans
Create Date: 2026-11-06 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "subscription_billing_period"
down_revision: str | Sequence[str] | None = "subscription_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("billing_period", sa.String(length=10), server_default="monthly", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_subscriptions_billing_period_valid"),
        "subscriptions",
        "billing_period IN ('monthly', 'biannual', 'annual')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_subscriptions_billing_period_valid"), "subscriptions", type_="check")
    op.drop_column("subscriptions", "billing_period")
