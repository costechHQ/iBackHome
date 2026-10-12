"""Request and response shapes for milestones."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.features.milestones.models import MilestoneStatus


class MilestoneGroup(BaseModel):
    """One milestone to create from the approved BoQ (built by Christopher's BoQ approval)."""

    name: str = Field(min_length=1, max_length=120)
    amount_minor: int = Field(gt=0, description="Total for this milestone in minor units (e.g. kobo)")


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    sequence: int
    name: str
    amount_minor: int
    currency: str
    status: MilestoneStatus
    funded_at: datetime | None
    claimed_at: datetime | None
    verified_at: datetime | None
    approved_at: datetime | None
    released_at: datetime | None
