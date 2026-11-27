"""Contractor match requests and shortlists (ADR 0007, phase 2).

match_requests: a client asks ops to find a contractor for a draft project; one active (open or shortlisted)
request per project. match_shortlist: the 1 to 3 contractors ops put forward.

Revision ID: match_requests
Revises: contractor_applications
Create Date: 2026-11-27 17:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "match_requests"
down_revision: str | Sequence[str] | None = "contractor_applications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=60), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("work_type", sa.String(length=20), nullable=False),
        sa.Column("timeline", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("budget_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("shortlist_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chosen_contractor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("ops_emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'shortlisted', 'matched', 'cancelled')",
            name=op.f("ck_match_requests_status_valid"),
        ),
        sa.CheckConstraint(
            "work_type IN ('buildings', 'roofing', 'finishing', 'civil_works', 'other')",
            name=op.f("ck_match_requests_work_type_valid"),
        ),
        sa.CheckConstraint("budget_minor > 0", name=op.f("ck_match_requests_budget_positive")),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_match_requests_project_id_projects")
        ),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], name=op.f("fk_match_requests_client_id_users")),
        sa.ForeignKeyConstraint(
            ["chosen_contractor_id"], ["users.id"], name=op.f("fk_match_requests_chosen_contractor_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_requests")),
    )
    op.create_index(op.f("ix_match_requests_project_id"), "match_requests", ["project_id"])
    op.create_index(
        "uq_match_requests_one_active_per_project",
        "match_requests",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'shortlisted')"),
    )
    op.create_index("ix_match_requests_status_created_at", "match_requests", ["status", "created_at"])

    op.create_table(
        "match_shortlist",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position BETWEEN 1 AND 3", name=op.f("ck_match_shortlist_position_range")),
        sa.ForeignKeyConstraint(
            ["request_id"], ["match_requests.id"], name=op.f("fk_match_shortlist_request_id_match_requests")
        ),
        sa.ForeignKeyConstraint(
            ["contractor_id"],
            ["contractor_profiles.id"],
            name=op.f("fk_match_shortlist_contractor_id_contractor_profiles"),
        ),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], name=op.f("fk_match_shortlist_added_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_shortlist")),
        sa.UniqueConstraint("request_id", "contractor_id", name="uq_match_shortlist_request_contractor"),
        sa.UniqueConstraint("request_id", "position", name="uq_match_shortlist_request_position"),
    )
    op.create_index(op.f("ix_match_shortlist_request_id"), "match_shortlist", ["request_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_match_shortlist_request_id"), table_name="match_shortlist")
    op.drop_table("match_shortlist")
    op.drop_index("ix_match_requests_status_created_at", table_name="match_requests")
    op.drop_index("uq_match_requests_one_active_per_project", table_name="match_requests")
    op.drop_index(op.f("ix_match_requests_project_id"), table_name="match_requests")
    op.drop_table("match_requests")
