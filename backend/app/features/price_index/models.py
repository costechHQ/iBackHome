"""Price index observations. 

One row = one supplier's price for one item on one day. The "current price" of an item is
worked out from these rows in service.current_prices(); nothing here is overwritten except
a re-loaded observation for the same item, supplier and day.

`supplier_id` has no database foreign key yet because the `suppliers` table (Abigail) does
not exist on day 1. The survey records suppliers by name until then.
"""

import uuid
from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class PriceIndexEntry(TimestampedBase):
    __tablename__ = "price_index_entries"
    __table_args__ = (
        UniqueConstraint(
            "item_key", "supplier_name", "observed_on", name="uq_price_index_entries_observation"
        ),
        CheckConstraint("price_minor > 0", name="price_positive"),
    )

    item_key: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    item: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(String(60), nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN", server_default="NGN")
    supplier_name: Mapped[str] = mapped_column(String(120), nullable=False)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(60), nullable=False, default="survey", server_default="survey")
