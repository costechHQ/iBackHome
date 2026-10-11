"""Database tables for payments. Owner: Gabriel.

`ledger_entries` is the double-entry ledger (spec: "Payments, escrow and ledger").
Rows are append-only: the migration installs triggers that reject UPDATE and DELETE,
and a deferred constraint trigger that rejects, at commit, any transaction_id whose
debits and credits differ or that mixes currencies. Write rows only through
`service.post_transaction`.
"""

import uuid
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class LedgerEntry(TimestampedBase):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint("direction IN ('debit', 'credit')", name="direction_valid"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
        CheckConstraint("fx_rate IS NULL OR fx_rate > 0", name="fx_rate_positive"),
        Index("ix_ledger_entries_ref_type_ref_id", "ref_type", "ref_id"),
        Index("ix_ledger_entries_account", "account"),
        Index("ix_ledger_entries_transaction_id", "transaction_id"),
        Index("ix_ledger_entries_created_at_id", "created_at", "id"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    account: Mapped[str] = mapped_column(String(200), nullable=False)
    direction: Mapped[str] = mapped_column(String(6), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    ref_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
