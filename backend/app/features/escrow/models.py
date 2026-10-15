"""Database tables for escrow. Owner: Gabriel.

`escrow_accounts`: one per project, the partner's account that holds that project's money.
`balance_minor` is a CACHE for fast reads. The ledger (`escrow:{project}:{currency}` in
ledger_entries) is the source of truth; reconciliation compares the two and the ledger wins.
Change it only through `service.py`, in the same transaction as the ledger entries.

`escrow_holds` (NOT in the spec yet; spec addition in the day-4 PR): one per funded milestone,
the partner's id for the money it holds (`provider_ref`), which a release has to name.

`escrow_releases`: money leaving escrow, to the contractor for a milestone or to a supplier for a
delivered order (exactly one of `milestone_id` / `order_id`). Status follows the spec:
requested -> submitted -> released, or failed. At most one release that has not failed per
milestone and per order (partial unique indexes), so a retried request never releases twice.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class EscrowAccount(TimestampedBase):
    __tablename__ = "escrow_accounts"
    __table_args__ = (
        CheckConstraint("balance_minor >= 0", name="balance_not_negative"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), unique=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_account_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")


class EscrowHold(TimestampedBase):
    """The partner holding one milestone's money (written when Stripe's payment is held)."""

    __tablename__ = "escrow_holds"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
        CheckConstraint("status IN ('held', 'pending')", name="status_valid"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id"), unique=True, nullable=False
    )
    ref: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)  # ours, sent to hold()
    provider_ref: Mapped[str] = mapped_column(String(255), nullable=False)  # the partner's, for release()
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)


class EscrowRelease(TimestampedBase):
    __tablename__ = "escrow_releases"
    __table_args__ = (
        CheckConstraint("(milestone_id IS NULL) <> (order_id IS NULL)", name="one_purpose"),
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
        CheckConstraint("status IN ('requested', 'submitted', 'released', 'failed')", name="status_valid"),
        Index(
            "uq_escrow_releases_open_milestone",
            "milestone_id",
            unique=True,
            postgresql_where=text("milestone_id IS NOT NULL AND status <> 'failed'"),
        ),
        Index(
            "uq_escrow_releases_open_order",
            "order_id",
            unique=True,
            postgresql_where=text("order_id IS NOT NULL AND status <> 'failed'"),
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id"), index=True, nullable=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_orders.id"), index=True, nullable=True
    )
    hold_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("escrow_holds.id"), index=True, nullable=False
    )
    payee: Mapped[str] = mapped_column(String(100), nullable=False)  # "contractor:<id>" / "supplier:<id>"
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="requested")
    provider_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Dispute(TimestampedBase):
    """A client contesting a verified milestone. open -> resolved_release | resolved_reject.

    Resolving needs two different ops users (spec): the first proposes an outcome
    (`proposed_*`, NOT in the spec yet: spec addition), a second confirms the same outcome.
    At most one open dispute per milestone (partial unique index).
    """

    __tablename__ = "disputes"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'resolved_release', 'resolved_reject')", name="status_valid"),
        CheckConstraint(
            "proposed_outcome IS NULL OR proposed_outcome IN ('release', 'rework')",
            name="proposed_outcome_valid",
        ),
        CheckConstraint("resolved_by IS NULL OR resolved_by <> proposed_by", name="two_ops_users"),
        Index(
            "uq_disputes_open_milestone",
            "milestone_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id"), index=True, nullable=False
    )
    raised_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    proposed_outcome: Mapped[str | None] = mapped_column(String(10), nullable=True)
    proposed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    proposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
