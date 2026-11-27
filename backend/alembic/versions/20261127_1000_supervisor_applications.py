"""Supervisor applications from the public form on /supervisors (ADR 0005, slice 1).

One pending application per phone and per email (partial unique indexes). There is no NIN column: ops check
the registration number first and ask for the NIN only afterwards.

Revision ID: supervisor_applications
Revises: subscription_billing_period
Create Date: 2026-11-27 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "supervisor_applications"
down_revision: str | Sequence[str] | None = "subscription_billing_period"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supervisor_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("state", sa.String(length=60), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("registration_body", sa.String(length=20), nullable=False),
        sa.Column("registration_no", sa.String(length=60), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=False),
        sa.Column("guarantor_1_name", sa.String(length=200), nullable=False),
        sa.Column("guarantor_1_phone", sa.String(length=16), nullable=False),
        sa.Column("guarantor_2_name", sa.String(length=200), nullable=False),
        sa.Column("guarantor_2_phone", sa.String(length=16), nullable=False),
        sa.Column("relatives", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_ip", sa.String(length=45), nullable=False),
        sa.Column("ops_emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("receipt_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending')", name=op.f("ck_supervisor_applications_status_valid")),
        sa.CheckConstraint(
            "registration_body IN ('COREN', 'NIOB', 'CORBON', 'other')",
            name=op.f("ck_supervisor_applications_registration_body_valid"),
        ),
        sa.CheckConstraint(
            "years_experience BETWEEN 0 AND 60",
            name=op.f("ck_supervisor_applications_years_experience_range"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supervisor_applications")),
    )
    op.create_index(
        "uq_supervisor_applications_pending_phone",
        "supervisor_applications",
        ["phone"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "uq_supervisor_applications_pending_email",
        "supervisor_applications",
        ["email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_supervisor_applications_requested_ip_created_at",
        "supervisor_applications",
        ["requested_ip", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_supervisor_applications_requested_ip_created_at", table_name="supervisor_applications")
    op.drop_index("uq_supervisor_applications_pending_email", table_name="supervisor_applications")
    op.drop_index("uq_supervisor_applications_pending_phone", table_name="supervisor_applications")
    op.drop_table("supervisor_applications")
