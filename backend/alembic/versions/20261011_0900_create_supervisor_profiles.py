"""Create the supervisor_profiles and supervisor_relations tables.

Revision ID: create_supervisor_profiles
Revises: 0001_base
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_supervisor_profiles"
down_revision: str | Sequence[str] | None = "0001_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

vetting_status = postgresql.ENUM("pending", "approved", "rejected", name="vetting_status", create_type=False)


def upgrade() -> None:
    vetting_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "supervisor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("registration_body", sa.String(120), nullable=False),
        sa.Column("registration_no", sa.String(60), nullable=False),
        sa.Column("guarantor_1", sa.String(200), nullable=False),
        sa.Column("guarantor_2", sa.String(200), nullable=False),
        sa.Column("registration_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("nin_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("guarantor_1_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("guarantor_2_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("vetting_status", vetting_status, server_default="pending", nullable=False),
        sa.Column("vetted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vetted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_supervisor_profiles_rating_range"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_supervisor_profiles"),
        sa.UniqueConstraint("user_id", name="uq_supervisor_profiles_user_id"),
    )
    op.create_table(
        "supervisor_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supervisor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_phone", sa.String(20), nullable=False),
        sa.Column("relationship", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_supervisor_relations"),
        sa.UniqueConstraint(
            "supervisor_id", "contractor_phone", name="uq_supervisor_relations_supervisor_phone"
        ),
    )
    op.create_index("ix_supervisor_relations_supervisor_id", "supervisor_relations", ["supervisor_id"])


def downgrade() -> None:
    op.drop_index("ix_supervisor_relations_supervisor_id", table_name="supervisor_relations")
    op.drop_table("supervisor_relations")
    op.drop_table("supervisor_profiles")
    vetting_status.drop(op.get_bind(), checkfirst=True)
