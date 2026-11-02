"""Add the supervisor's NIN: encrypted while pending, then only the last 4 digits.

nin_encrypted holds the full NIN (Fernet) only until ops approve or reject, then is set to NULL.
nin_last4 stays. The column is kept out of the audit log (see features/supervision/nin.py).

Revision ID: supervisor_nin
Revises: report_note_reviewer
Create Date: 2026-11-02 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "supervisor_nin"
down_revision: str | Sequence[str] | None = "report_note_reviewer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("supervisor_profiles", sa.Column("nin_encrypted", sa.Text(), nullable=True))
    op.add_column("supervisor_profiles", sa.Column("nin_last4", sa.String(length=4), nullable=True))


def downgrade() -> None:
    op.drop_column("supervisor_profiles", "nin_last4")
    op.drop_column("supervisor_profiles", "nin_encrypted")
