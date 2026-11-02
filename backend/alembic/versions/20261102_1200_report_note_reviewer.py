"""Add the supervisor's note and the reviewer to weekly reports.

supervisor_note: what the reviewing supervisor (or ops) adds under their own name while the report is a
draft (the design: "your note to <client>, shown under your name"). note_by: who wrote it. reviewed_by:
who marked the report reviewed (the design: "Reviewed by <name>"). The AI body is never changed.

Revision ID: report_note_reviewer
Revises: create_push_tokens
Create Date: 2026-11-02 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "report_note_reviewer"
down_revision: str | Sequence[str] | None = "create_push_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("supervisor_note", sa.Text(), nullable=True))
    op.add_column("reports", sa.Column("note_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("reports", sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_reports_note_by_users", "reports", "users", ["note_by"], ["id"])
    op.create_foreign_key("fk_reports_reviewed_by_users", "reports", "users", ["reviewed_by"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_reports_reviewed_by_users", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_note_by_users", "reports", type_="foreignkey")
    op.drop_column("reports", "reviewed_by")
    op.drop_column("reports", "note_by")
    op.drop_column("reports", "supervisor_note")
