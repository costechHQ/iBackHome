"""Add NDPA 2023 consent to users: the terms and privacy versions agreed to, and when.

Revision ID: add_user_consent
Revises: create_notifications
Create Date: 2026-10-22 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "add_user_consent"
down_revision: str | Sequence[str] | None = "create_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("terms_version", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("privacy_version", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "consented_at")
    op.drop_column("users", "privacy_version")
    op.drop_column("users", "terms_version")
