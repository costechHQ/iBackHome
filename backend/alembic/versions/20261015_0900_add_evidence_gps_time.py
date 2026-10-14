"""Add the GPS fix time to evidence, for the clock check.

Revision ID: add_evidence_gps_time
Revises: create_evidence_and_suppliers
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "add_evidence_gps_time"
down_revision: str | Sequence[str] | None = "create_evidence_and_suppliers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("gps_time", sa.DateTime(timezone=True), nullable=True))
    # Rows saved before this column existed have no GPS time; treat their capture time as it.
    op.execute("UPDATE evidence SET gps_time = captured_at WHERE gps_time IS NULL")
    op.alter_column("evidence", "gps_time", nullable=False)


def downgrade() -> None:
    op.drop_column("evidence", "gps_time")
