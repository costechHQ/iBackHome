"""Database tables for escrow. Owner: Gabriel.

`escrow_accounts`: one per project, the partner's account that holds that project's money.
`balance_minor` is a CACHE for fast reads. The ledger (`escrow:{project}:{currency}` in
ledger_entries) is the source of truth; reconciliation compares the two and the ledger wins.
Change it only through `service.py`, in the same transaction as the ledger entries.
"""

import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
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
