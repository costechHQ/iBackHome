"""Request and response shapes (Pydantic) for subscriptions. Owner: Christopher."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.features.subscriptions.plans import PlanCode, visits_for


class PlanOut(BaseModel):
    code: PlanCode
    name: str
    visits_per_month: int = Field(description="Supervisor site visits each month")
    currency: str = Field(description="Always USD")
    amount_minor: int = Field(description="Charged every month, in US cents")
    recommended: bool


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: PlanCode = Field(description="basic, standard or premium")
    currency: Literal["USD"] = Field(default="USD", description="Clients pay in USD only")


class SubscriptionCheckoutOut(BaseModel):
    project_id: uuid.UUID
    checkout_session_id: str
    checkout_url: str
    plan: PlanCode
    visits_per_month: int
    currency: str
    amount_minor: int = Field(description="Charged every month")


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    status: Literal["incomplete", "active", "past_due", "canceled"]
    plan: PlanCode
    currency: str
    amount_minor: int
    current_period_end: datetime | None
    cancel_at_period_end: bool
    past_due_since: datetime | None
    paused_by_billing: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def visits_per_month(self) -> int:
        return visits_for(self.plan)
