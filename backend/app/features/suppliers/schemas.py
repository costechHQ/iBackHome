"""Request and response shapes (Pydantic) for suppliers. Owner: Abigail."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderItem(BaseModel):
    item: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=40)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_price_minor: int = Field(strict=True, gt=0, le=10**12)  # integer minor units (kobo), never a float

    @field_validator("quantity", mode="before")
    @classmethod
    def _no_floats(cls, value: object) -> object:
        # 0.1 + 0.2 style surprises: accept numbers as strings or ints, or floats via their text.
        return str(value) if isinstance(value, float) else value


class OrderRequest(BaseModel):
    supplier_id: uuid.UUID
    items: list[OrderItem] = Field(min_length=1, max_length=50)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    supplier_id: uuid.UUID
    requested_by: uuid.UUID
    items: list[dict[str, object]]
    total_minor: int
    currency: str
    status: str
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime
