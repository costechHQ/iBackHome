"""payout_recipients.supplier_id -> suppliers, and single check-constraint names on payments tables.

- Foreign key payout_recipients.supplier_id -> suppliers.id (suppliers landed after payouts).
- The earlier payments migrations passed full names that the naming convention prefixed again
  ("ck_payouts_ck_payouts_amount_positive"). Renamed to what the models expect
  ("ck_payouts_amount_positive"). Cosmetic: the checks themselves are unchanged.

Owner: Gabriel.

Revision ID: payout_recipient_supplier_fk
Revises: create_escrow_releases
Create Date: 2026-10-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "payout_recipient_supplier_fk"
down_revision: str | Sequence[str] | None = "create_escrow_releases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# table -> constraint suffixes that were doubled
DOUBLED = {
    "ledger_entries": ["amount_positive", "currency_iso4217", "direction_valid", "fx_rate_positive"],
    "payment_events": ["provider_valid"],
    "escrow_accounts": ["balance_not_negative", "currency_iso4217"],
    "payout_recipients": ["account_number_masked", "one_owner", "provider_valid"],
    "payouts": ["amount_positive", "status_valid"],
}


def _rename(old: str, new: str, table: str) -> None:
    op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT "{old}" TO "{new}"')


def upgrade() -> None:
    op.create_foreign_key(
        op.f("fk_payout_recipients_supplier_id_suppliers"),
        "payout_recipients",
        "suppliers",
        ["supplier_id"],
        ["id"],
    )
    for table, suffixes in DOUBLED.items():
        for suffix in suffixes:
            _rename(f"ck_{table}_ck_{table}_{suffix}", f"ck_{table}_{suffix}", table)


def downgrade() -> None:
    for table, suffixes in DOUBLED.items():
        for suffix in suffixes:
            _rename(f"ck_{table}_{suffix}", f"ck_{table}_ck_{table}_{suffix}", table)
    op.drop_constraint(
        op.f("fk_payout_recipients_supplier_id_suppliers"), "payout_recipients", type_="foreignkey"
    )
