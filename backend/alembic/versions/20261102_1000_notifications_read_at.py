"""Add read_at to notifications, so the in-app feed can show what was read.

Revision ID: notifications_read_at
Revises: create_subscriptions
Create Date: 2026-11-02 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "notifications_read_at"
down_revision: str | Sequence[str] | None = "create_subscriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("notifications", "read_at")
