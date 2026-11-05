"""Subscription plans: a `plan` column (basic, standard, premium) on subscriptions.

Existing rows become `basic`; their stored price is unchanged until they renew on a plan.

Revision ID: subscription_plans
Revises: checklist_templates
Create Date: 2026-11-05 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "subscription_plans"
down_revision: str | Sequence[str] | None = "checklist_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("plan", sa.String(length=16), server_default="basic", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_subscriptions_plan_valid"), "subscriptions", "plan IN ('basic', 'standard', 'premium')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_subscriptions_plan_valid"), "subscriptions", type_="check")
    op.drop_column("subscriptions", "plan")
