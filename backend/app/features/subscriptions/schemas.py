"""Request and response shapes (Pydantic) for subscriptions. Owner: Christopher."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.features.subscriptions.plans import BillingPeriod, PlanCode, visits_for


class PeriodPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: BillingPeriod
    months: int = Field(description="Months covered by one invoice")
    paid_months: int = Field(description="Months paid for; the rest are free")
    amount_minor: int = Field(description="Charged each billing period, in US cents")
    list_amount_minor: int = Field(description="The same months at the monthly price, before the discount")
    monthly_equivalent_minor: int = Field(description="amount_minor spread over the months, rounded down")


class PlanOut(BaseModel):
    code: PlanCode
    name: str
    visits_per_month: int = Field(description="Supervisor site visits each month")
    currency: str = Field(description="Always USD")
    amount_minor: int = Field(description="The monthly price, in US cents")
    recommended: bool
    periods: list[PeriodPriceOut] = Field(description="Price of one invoice for each billing period")


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: PlanCode = Field(description="basic, standard or premium")
    billing_period: BillingPeriod = Field(
        default="monthly", description="monthly, biannual (6 months, pay 5) or annual (12 months, pay 10)"
    )
    currency: Literal["USD"] = Field(default="USD", description="Clients pay in USD only")


class SubscriptionCheckoutOut(BaseModel):
    project_id: uuid.UUID
    checkout_session_id: str
    checkout_url: str
    plan: PlanCode
    billing_period: BillingPeriod
    visits_per_month: int
    currency: str
    amount_minor: int = Field(description="Charged each billing period")


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    status: Literal["incomplete", "active", "past_due", "canceled"]
    plan: PlanCode
    billing_period: BillingPeriod
    currency: str
    amount_minor: int = Field(description="Charged each billing period")
    current_period_end: datetime | None
    cancel_at_period_end: bool
    past_due_since: datetime | None
    paused_by_billing: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def visits_per_month(self) -> int:
        return visits_for(self.plan)
