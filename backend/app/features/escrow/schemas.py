"""Request and response shapes (Pydantic) for escrow. Owner: Gabriel."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.base.payments.fx import FundingCurrency


class FundingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    milestone_id: uuid.UUID
    currency: FundingCurrency = Field(description="The currency the client pays in: GBP, USD or EUR")


class FundingQuoteOut(BaseModel):
    """What funding a milestone would cost today, before going to Stripe. Nothing is recorded."""

    milestone_id: uuid.UUID
    currency: str
    amount_ngn_minor: int = Field(description="What the escrow will hold, in kobo")
    net_minor: int = Field(description="amount_ngn_minor converted at fx_rate, rounded up")
    fee_minor: int
    fee_bps: int
    total_minor: int = Field(description="net_minor + fee_minor: what the client would pay")
    fx_rate: Decimal = Field(description="NGN per 1 unit of currency (fixed when they pay)")
    fx_as_of: datetime


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


class LedgerEntryOut(BaseModel):
    """One ledger line. Amounts are integer minor units; fx_rate is a decimal string."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    account: str
    direction: str = Field(description="debit or credit")
    amount_minor: int
    currency: str
    fx_rate: Decimal | None
    ref_type: str
    ref_id: uuid.UUID
    created_at: datetime


class LedgerPage(BaseModel):
    items: list[LedgerEntryOut]
    next_cursor: str | None


class DisputeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=2000, description="What is wrong with the work")


class DisputeResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["release", "rework"] = Field(
        description="release: the contractor is paid; rework: back to funded, the contractor fixes it"
    )
    notes: str = Field(min_length=1, max_length=2000)


class DisputeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    milestone_id: uuid.UUID
    raised_by: uuid.UUID
    reason: str
    status: str = Field(description="open, resolved_release or resolved_reject")
    proposed_outcome: str | None = Field(description="The first ops approval's outcome")
    proposed_by: uuid.UUID | None
    proposed_at: datetime | None
    resolution_notes: str | None
    resolved_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class DisputeResolutionOut(BaseModel):
    dispute: DisputeOut
    resolved: bool = Field(description="False: first ops approval recorded; a second ops user must confirm")
    release_id: uuid.UUID | None = Field(description="The release requested when resolved for release")
