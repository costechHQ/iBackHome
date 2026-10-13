"""Create the audit_log table and make it insert-only.

Two protections, so an edit is refused by the database itself:
1. A trigger that raises an error on every UPDATE, DELETE or TRUNCATE. This works for every
   database user, including the superuser that Docker creates for local development.
2. UPDATE, DELETE and TRUNCATE rights removed from the app's database user and from PUBLIC.

Revision ID: create_audit_log
Revises: create_price_index
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_audit_log"
down_revision: str | Sequence[str] | None = "create_price_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("object_type", sa.String(60), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("device_id", sa.String(128), nullable=True),
        sa.Column(
            "at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
    )
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_object", "audit_log", ["object_type", "object_id"])
    op.create_index("ix_audit_log_at_id", "audit_log", ["at", "id"])

    op.execute(
        """
        CREATE FUNCTION audit_log_refuse_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is insert-only: % is not allowed', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER audit_log_no_update_or_delete BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_log_refuse_change()"
    )
    op.execute(
        "CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_log_refuse_change()"
    )
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM PUBLIC")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM CURRENT_USER")


def downgrade() -> None:
    op.drop_table("audit_log")  # also drops its indexes and triggers
    op.execute("DROP FUNCTION IF EXISTS audit_log_refuse_change()")
