"""Create the ledger_entries table and the database guards that protect it.

- A DEFERRABLE INITIALLY DEFERRED constraint trigger checks, at commit, that every
  transaction_id touched has sum(debits) = sum(credits) and exactly one currency.
- BEFORE UPDATE/DELETE/TRUNCATE triggers make the table append-only for every role
  (including superusers and the owner, which REVOKE alone cannot stop).
- UPDATE, DELETE and TRUNCATE are revoked from PUBLIC and from the app role
  (LEDGER_APP_ROLE, default "ibackhome"); skipped with a notice if that role does not exist.

Owner: Gabriel.

Revision ID: create_ledger_entries
Revises: create_spot_checks
Create Date: 2026-10-11
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.base.payments.settings import get_payments_settings

revision: str = "create_ledger_entries"
down_revision: str | Sequence[str] | None = "create_spot_checks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHECK_BALANCED_FN = """
CREATE FUNCTION ledger_entries_check_balanced() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    total_debit  bigint;
    total_credit bigint;
    currencies   integer;
BEGIN
    SELECT COALESCE(SUM(amount_minor) FILTER (WHERE direction = 'debit'), 0),
           COALESCE(SUM(amount_minor) FILTER (WHERE direction = 'credit'), 0),
           COUNT(DISTINCT currency)
      INTO total_debit, total_credit, currencies
      FROM ledger_entries
     WHERE transaction_id = NEW.transaction_id;

    IF total_debit <> total_credit THEN
        RAISE EXCEPTION 'ledger transaction % is unbalanced: debits %, credits %',
            NEW.transaction_id, total_debit, total_credit
            USING ERRCODE = 'check_violation', CONSTRAINT = 'ledger_entries_balanced';
    END IF;
    IF currencies <> 1 THEN
        RAISE EXCEPTION 'ledger transaction % mixes % currencies', NEW.transaction_id, currencies
            USING ERRCODE = 'check_violation', CONSTRAINT = 'ledger_entries_single_currency';
    END IF;
    RETURN NULL;
END;
$$;
"""

REJECT_CHANGE_FN = """
CREATE FUNCTION ledger_entries_reject_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'ledger_entries is append-only: % is not allowed', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$;
"""

_ROLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,62}$")


def _revoke_sql(role: str) -> str:
    if not _ROLE_NAME.match(role):
        raise ValueError(f"LEDGER_APP_ROLE {role!r} is not a plain Postgres role name")
    return f"""
DO $$
BEGIN
    REVOKE UPDATE, DELETE, TRUNCATE ON ledger_entries FROM PUBLIC;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
        EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON ledger_entries FROM %I', '{role}');
    ELSE
        RAISE NOTICE 'role % does not exist; skipped REVOKE on ledger_entries', '{role}';
    END IF;
END;
$$;
"""  # noqa: S608 - role checked against _ROLE_NAME above


def upgrade() -> None:
    op.create_table(
        "ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account", sa.String(200), nullable=False),
        sa.Column("direction", sa.String(6), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("fx_rate", sa.Numeric(20, 10), nullable=True),
        sa.Column("ref_type", sa.String(50), nullable=False),
        sa.Column("ref_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_entries"),
        sa.CheckConstraint("amount_minor > 0", name="ck_ledger_entries_amount_positive"),
        sa.CheckConstraint("direction IN ('debit', 'credit')", name="ck_ledger_entries_direction_valid"),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_ledger_entries_currency_iso4217"),
        sa.CheckConstraint("fx_rate IS NULL OR fx_rate > 0", name="ck_ledger_entries_fx_rate_positive"),
    )
    op.create_index("ix_ledger_entries_ref_type_ref_id", "ledger_entries", ["ref_type", "ref_id"])
    op.create_index("ix_ledger_entries_account", "ledger_entries", ["account"])
    op.create_index("ix_ledger_entries_transaction_id", "ledger_entries", ["transaction_id"])
    op.create_index("ix_ledger_entries_created_at_id", "ledger_entries", ["created_at", "id"])

    op.execute(CHECK_BALANCED_FN)
    op.execute(
        "CREATE CONSTRAINT TRIGGER ledger_entries_balanced "
        "AFTER INSERT ON ledger_entries "
        "DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION ledger_entries_check_balanced()"
    )

    op.execute(REJECT_CHANGE_FN)
    op.execute(
        "CREATE TRIGGER ledger_entries_append_only "
        "BEFORE UPDATE OR DELETE ON ledger_entries "
        "FOR EACH ROW EXECUTE FUNCTION ledger_entries_reject_change()"
    )
    op.execute(
        "CREATE TRIGGER ledger_entries_no_truncate "
        "BEFORE TRUNCATE ON ledger_entries "
        "FOR EACH STATEMENT EXECUTE FUNCTION ledger_entries_reject_change()"
    )

    op.execute(_revoke_sql(get_payments_settings().ledger_app_role))


def downgrade() -> None:
    # Dropping the table drops its triggers and grants with it.
    op.drop_table("ledger_entries")
    op.execute("DROP FUNCTION IF EXISTS ledger_entries_reject_change()")
    op.execute("DROP FUNCTION IF EXISTS ledger_entries_check_balanced()")
