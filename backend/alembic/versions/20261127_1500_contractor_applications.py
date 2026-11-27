"""Contractor applications and profiles (ADR 0007, phase 1).

contractor_applications: the public form on /contractors, one pending application per phone and per email.
contractor_profiles: an approved contractor, created when ops approve an application (the directory phase 2
shortlists from). No NIN column: ops check registration and references first.

Revision ID: contractor_applications
Revises: supervisor_applications
Create Date: 2026-11-27 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "contractor_applications"
down_revision: str | Sequence[str] | None = "supervisor_applications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contractor_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("contact_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("states_served", postgresql.JSONB(), nullable=False),
        sa.Column("specialties", postgresql.JSONB(), nullable=False),
        sa.Column("years_in_business", sa.Integer(), nullable=False),
        sa.Column("projects_completed", sa.Integer(), nullable=False),
        sa.Column("cac_rc_number", sa.String(length=30), nullable=True),
        sa.Column("corbon_number", sa.String(length=40), nullable=True),
        sa.Column("reference_1_name", sa.String(length=200), nullable=False),
        sa.Column("reference_1_phone", sa.String(length=16), nullable=False),
        sa.Column("reference_2_name", sa.String(length=200), nullable=False),
        sa.Column("reference_2_phone", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("registration_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reference_1_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reference_2_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("ops_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_ip", sa.String(length=45), nullable=False),
        sa.Column("ops_emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("receipt_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name=op.f("ck_contractor_applications_status_valid"),
        ),
        sa.CheckConstraint(
            "years_in_business BETWEEN 0 AND 80",
            name=op.f("ck_contractor_applications_years_in_business_range"),
        ),
        sa.CheckConstraint(
            "projects_completed BETWEEN 0 AND 10000",
            name=op.f("ck_contractor_applications_projects_completed_range"),
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"], ["users.id"], name=op.f("fk_contractor_applications_decided_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contractor_applications")),
    )
    op.create_index(
        "uq_contractor_applications_pending_phone",
        "contractor_applications",
        ["phone"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "uq_contractor_applications_pending_email",
        "contractor_applications",
        ["email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_contractor_applications_requested_ip_created_at",
        "contractor_applications",
        ["requested_ip", "created_at"],
    )
    op.create_index(
        "ix_contractor_applications_status_created_at", "contractor_applications", ["status", "created_at"]
    )

    op.create_table(
        "contractor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("contact_name", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("states_served", postgresql.JSONB(), nullable=False),
        sa.Column("specialties", postgresql.JSONB(), nullable=False),
        sa.Column("years_in_business", sa.Integer(), nullable=False),
        sa.Column("projects_completed", sa.Integer(), nullable=False),
        sa.Column("vetting_status", sa.String(length=20), server_default="approved", nullable=False),
        sa.Column("vetted_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vetted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("listed", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "vetting_status IN ('approved', 'suspended')",
            name=op.f("ck_contractor_profiles_vetting_status_valid"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_contractor_profiles_user_id_users")),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["contractor_applications.id"],
            name=op.f("fk_contractor_profiles_application_id_contractor_applications"),
        ),
        sa.ForeignKeyConstraint(
            ["vetted_by"], ["users.id"], name=op.f("fk_contractor_profiles_vetted_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contractor_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_contractor_profiles_user_id")),
    )
    op.create_index(
        "ix_contractor_profiles_listed_vetting_status", "contractor_profiles", ["listed", "vetting_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_contractor_profiles_listed_vetting_status", table_name="contractor_profiles")
    op.drop_table("contractor_profiles")
    op.drop_index("ix_contractor_applications_status_created_at", table_name="contractor_applications")
    op.drop_index("ix_contractor_applications_requested_ip_created_at", table_name="contractor_applications")
    op.drop_index("uq_contractor_applications_pending_email", table_name="contractor_applications")
    op.drop_index("uq_contractor_applications_pending_phone", table_name="contractor_applications")
    op.drop_table("contractor_applications")
