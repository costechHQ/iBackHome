"""Request and response shapes (Pydantic) for subscriptions. Owner: Christopher."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.base.payments.fx import FundingCurrency


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: FundingCurrency = Field(description="The currency the client pays in: GBP, USD or EUR")


class SubscriptionCheckoutOut(BaseModel):
    project_id: uuid.UUID
    checkout_session_id: str
    checkout_url: str
    currency: str
    amount_minor: int = Field(description="Charged every month")


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    status: Literal["incomplete", "active", "past_due", "canceled"]
    currency: str
    amount_minor: int
    current_period_end: datetime | None
    cancel_at_period_end: bool
    past_due_since: datetime | None
    paused_by_billing: bool
