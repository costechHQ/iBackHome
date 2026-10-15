"""Request and response shapes for supervisor vetting, assignment and spot checks. Owner: James."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.features.supervision.models import VettingStatus


class DeclaredRelation(BaseModel):
    # Any form login accepts (0803..., +234803..., +44...); stored in E.164 like users.phone.
    contractor_phone: str = Field(min_length=7, max_length=20, examples=["08031234567"])
    relationship: str = Field(min_length=2, max_length=60, examples=["brother-in-law"])


class SupervisorApplication(BaseModel):
    """What a supervisor submits to be vetted."""

    registration_body: str = Field(min_length=2, max_length=120, examples=["COREN"])
    registration_no: str = Field(min_length=2, max_length=60)
    guarantor_1: str = Field(min_length=5, max_length=200, examples=["Ngozi Eze, +2348031234567"])
    guarantor_2: str = Field(min_length=5, max_length=200)
    related_contractors: list[DeclaredRelation] = Field(default_factory=list, max_length=20)


class VettingDecision(BaseModel):
    """Ops' decision. Approval needs every check ticked; rejection needs a reason."""

    decision: Literal["approved", "rejected"]
    registration_verified: bool = False
    nin_verified: bool = False
    guarantor_1_verified: bool = False
    guarantor_2_verified: bool = False
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _reason_when_rejected(self) -> Self:
        if self.decision == "rejected" and not (self.reason and self.reason.strip()):
            raise ValueError("a reason is required when rejecting")
        return self


class SupervisorProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    registration_body: str
    registration_no: str
    registration_verified: bool
    nin_verified: bool
    guarantor_1_verified: bool
    guarantor_2_verified: bool
    vetting_status: VettingStatus
    vetted_at: datetime | None
    rejection_reason: str | None
    rating: Decimal | None


class AssignSupervisor(BaseModel):
    supervisor_id: uuid.UUID


class ProjectSupervisorOut(BaseModel):
    project_id: uuid.UUID
    supervisor_id: uuid.UUID


class SpotCheckCreate(BaseModel):
    supervisor_id: uuid.UUID
    scheduled_for: AwareDatetime  # must carry a timezone; stored in UTC


class SpotCheckComplete(BaseModel):
    findings: str = Field(min_length=10, max_length=5000)


class SpotCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    supervisor_id: uuid.UUID
    scheduled_for: datetime
    completed_at: datetime | None
    findings: str | None
