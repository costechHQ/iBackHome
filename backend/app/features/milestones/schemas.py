"""Request and response shapes for milestones."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


# --- verify ----------------------------------------------------------------------------------

MAX_CHECKLIST_ITEMS = 50
MAX_PHOTOS_PER_ITEM = 20


class ChecklistItem(BaseModel):
    """One thing the supervisor checked on site, and the photos that show it."""

    item: str = Field(min_length=1, max_length=200, description="e.g. 'Foundation trench depth as drawn'")
    passed: bool
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_PHOTOS_PER_ITEM)


class VerifyIn(BaseModel):
    """The supervisor's decision on a claimed milestone.

    - `verified`: every checklist item passed and has at least one photo.
    - `rejected`: `notes` gives the reason the contractor sees; the checklist is optional.
    """

    decision: Literal["verified", "rejected"]
    checklist: list[ChecklistItem] = Field(default_factory=list, max_length=MAX_CHECKLIST_ITEMS)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check(self) -> "VerifyIn":
        if self.notes is not None:
            self.notes = self.notes.strip() or None
        if self.decision == "verified":
            if not self.checklist:
                raise ValueError("a verified milestone needs a checklist")
            if not all(i.passed for i in self.checklist):
                raise ValueError("every checklist item must pass to verify; reject with a reason instead")
            if not all(i.evidence_ids for i in self.checklist):
                raise ValueError("every checklist item needs at least one photo")
        elif self.notes is None:
            raise ValueError("a rejection needs a reason in notes")
        return self

    def evidence_ids(self) -> set[uuid.UUID]:
        return {e for i in self.checklist for e in i.evidence_ids}


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    milestone_id: uuid.UUID
    supervisor_id: uuid.UUID
    decision: Literal["verified", "rejected"]
    checklist: list[ChecklistItem]
    notes: str | None
    created_at: datetime


class VerifyOut(BaseModel):
    milestone: MilestoneOut
    verification: VerificationOut


class ProjectMilestoneOut(MilestoneOut):
    """A milestone in the project list, with its newest verification (if any).

    After a rejection the milestone is back to `funded`; `latest_verification.notes` says why.
    """

    latest_verification: VerificationOut | None = None
