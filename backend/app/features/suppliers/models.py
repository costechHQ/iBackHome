"""Tables for suppliers and the material orders contractors place with them. Owner: Abigail.

Other features read these only through suppliers/service.py.
Money is integer minor units plus a currency, never floats.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class OrderStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    DELIVERED = "delivered"
    PAID = "paid"
    CANCELLED = "cancelled"


def _one_of(column: str, values: type[StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(v.value) for v in values)})"


class Supplier(TimestampedBase):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    paystack_recipient_code: Mapped[str | None] = mapped_column(String(64))  # set by payments, not here


class MaterialOrder(TimestampedBase):
    __tablename__ = "material_orders"
    __table_args__ = (
        CheckConstraint(_one_of("status", OrderStatus), name="status_valid"),
        CheckConstraint("total_minor > 0", name="total_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # [{"item": "Cement", "unit": "bag", "quantity": "100", "unit_price_minor": 780000}, ...]
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=OrderStatus.REQUESTED.value,
        server_default=OrderStatus.REQUESTED.value,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
