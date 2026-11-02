"""Request and response shapes for milestones."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.features.milestones.models import MilestoneStatus

# What a supervisor checks when ops have not written a template for that kind of milestone. It is a fallback,
# not content: ops replace it, per milestone name, with PUT /checklist-templates (the wording is theirs).
DEFAULT_CHECKLIST: tuple[str, ...] = (
    "Work matches the bill of quantities",
    "Materials are as specified",
    "Workmanship is acceptable",
    "Site is safe and tidy",
)


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
    `checklist` is what the supervisor checks on site: ops' template for this milestone's name, copied in when
    the milestone was made, or the generic default where there was none.
    """

    latest_verification: VerificationOut | None = None
    checklist: list[str] = Field(default_factory=lambda: list(DEFAULT_CHECKLIST))

    @field_validator("checklist", mode="before")
    @classmethod
    def _default_when_none(cls, value: object) -> object:
        # A milestone made before templates existed has no checklist of its own: it reads as the default.
        return value if value else list(DEFAULT_CHECKLIST)


# --- checklist templates (ops) ----------------------------------------------------------------

MAX_ITEM_CHARS = 200


class ChecklistTemplateIn(BaseModel):
    """Ops' checklist for a kind of milestone. Replaces the template with this name, if there is one."""

    milestone_name: str = Field(min_length=1, max_length=120, examples=["Foundation"])
    items: list[str] = Field(min_length=1, max_length=MAX_CHECKLIST_ITEMS)

    @field_validator("milestone_name")
    @classmethod
    def _named(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("a milestone name is required")
        return value

    @field_validator("items")
    @classmethod
    def _clean_items(cls, items: list[str]) -> list[str]:
        cleaned = [" ".join(i.split()) for i in items]
        if any(not i for i in cleaned):
            raise ValueError("a checklist item can't be blank")
        if any(len(i) > MAX_ITEM_CHARS for i in cleaned):
            raise ValueError(f"a checklist item is at most {MAX_ITEM_CHARS} characters")
        if len({i.lower() for i in cleaned}) != len(cleaned):
            raise ValueError("a checklist item appears twice")
        return cleaned


class ChecklistTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    milestone_name: str
    items: list[str]
    updated_by: uuid.UUID | None
    updated_at: datetime
