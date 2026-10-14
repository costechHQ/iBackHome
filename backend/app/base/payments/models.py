"""Database tables for payments. Owner: Gabriel.

`ledger_entries` is the double-entry ledger (spec: "Payments, escrow and ledger").
Rows are append-only: the migration installs triggers that reject UPDATE and DELETE,
and a deferred constraint trigger that rejects, at commit, any transaction_id whose
debits and credits differ or that mixes currencies. Write rows only through
`service.post_transaction`.

`payment_events` stores every verified webhook once (unique provider + event_id), so a
re-delivered event is recognised and never processed twice. Write rows only through
`service.record_event`.

`payout_recipients` and `payouts` (NOT in the spec yet; proposed in the day-3 explainer):
a contractor's or supplier's Paystack recipient (bank account, stored MASKED: never the full
account number), and each NGN transfer we start, keyed by our own unique `reference` so a
retried transfer is never sent twice. Change them only through service.py.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


class PaymentEvent(TimestampedBase):
    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_payment_events_provider_event_id"),
        CheckConstraint("provider IN ('stripe', 'paystack', 'escrow')", name="provider_valid"),
    )

    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PayoutRecipient(TimestampedBase):
    """Where a contractor's or supplier's naira goes (a Paystack transfer recipient)."""

    __tablename__ = "payout_recipients"
    __table_args__ = (
        CheckConstraint("(user_id IS NULL) <> (supplier_id IS NULL)", name="one_owner"),
        CheckConstraint(r"account_number_masked ~ '^\*{6}[0-9]{4}$'", name="account_number_masked"),
        CheckConstraint("provider IN ('paystack')", name="provider_valid"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=True
    )
    # suppliers has no table yet (features/suppliers); add the foreign key when it lands.
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="paystack")
    recipient_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    bank_code: Mapped[str] = mapped_column(String(20), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number_masked: Mapped[str] = mapped_column(String(10), nullable=False)  # "******6789"
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN")


class Payout(TimestampedBase):
    """One NGN transfer to a recipient. Status follows Paystack's transfer.* webhooks."""

    __tablename__ = "payouts"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint("status IN ('pending', 'success', 'failed', 'reversed')", name="status_valid"),
    )

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payout_recipients.id"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="paystack")
    reference: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN")
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    provider_transfer_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
