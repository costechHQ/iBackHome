"""Link spot_checks.project_id to projects now that the projects table exists.

Revision ID: spot_checks_project_fk
Revises: create_boq
Create Date: 2026-10-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "spot_checks_project_fk"
down_revision: str | Sequence[str] | None = "create_boq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_spot_checks_project_id_projects", "spot_checks", "projects", ["project_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_spot_checks_project_id_projects", "spot_checks", type_="foreignkey")
