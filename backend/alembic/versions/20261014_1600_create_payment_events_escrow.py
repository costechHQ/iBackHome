"""Create payment_events (each webhook stored once) and escrow_accounts (one per project).

- payment_events: UNIQUE (provider, event_id) is what makes a re-delivered webhook a no-op.
- escrow_accounts: balance_minor is a cache; the ledger is the source of truth.

Owner: Gabriel.

Revision ID: create_payment_events_escrow
Revises: add_evidence_gps_time
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_payment_events_escrow"
down_revision: str | Sequence[str] | None = "add_evidence_gps_time"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "payment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_payment_events"),
        sa.UniqueConstraint("provider", "event_id", name="uq_payment_events_provider_event_id"),
        sa.CheckConstraint(
            "provider IN ('stripe', 'paystack', 'escrow')", name="ck_payment_events_provider_valid"
        ),
    )

    op.create_table(
        "escrow_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_account_ref", sa.String(255), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("balance_minor", sa.BigInteger(), server_default="0", nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_escrow_accounts"),
        sa.UniqueConstraint("project_id", name="uq_escrow_accounts_project_id"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="fk_escrow_accounts_project_id_projects"
        ),
        sa.CheckConstraint("balance_minor >= 0", name="ck_escrow_accounts_balance_not_negative"),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_escrow_accounts_currency_iso4217"),
    )


def downgrade() -> None:
    op.drop_table("escrow_accounts")
    op.drop_table("payment_events")
