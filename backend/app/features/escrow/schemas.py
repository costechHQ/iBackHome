"""Request and response shapes (Pydantic) for escrow. Owner: Gabriel."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.base.payments.fx import FundingCurrency


class FundingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    milestone_id: uuid.UUID
    currency: FundingCurrency = Field(description="The currency the client pays in: GBP, USD or EUR")


class FundingCheckoutOut(BaseModel):
    """What the client is about to pay. Nothing is in the ledger until Stripe confirms."""

    project_id: uuid.UUID
    milestone_id: uuid.UUID
    checkout_session_id: str
    checkout_url: str
    currency: str
    amount_ngn_minor: int = Field(description="What the escrow will hold, in kobo")
    net_minor: int = Field(description="amount_ngn_minor converted at fx_rate, rounded up")
    fee_minor: int
    fee_bps: int
    total_minor: int = Field(description="net_minor + fee_minor: what the client pays")
    fx_rate: Decimal = Field(description="NGN per 1 unit of currency")
    fx_as_of: datetime
