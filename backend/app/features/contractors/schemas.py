"""Request and response shapes for contractor applications, vetting and the directory. Owner: Christopher."""

import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SpecialtyName = Literal["buildings", "roofing", "finishing", "civil_works", "other"]


class ContractorApplicationIn(BaseModel):
    """What the website form sends. `extra="forbid"`: a field we never ask for (a NIN, say) is a 422, so one
    sent by mistake is refused instead of stored."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    business_name: str = Field(min_length=2, max_length=200)
    contact_name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=7, max_length=20, examples=["08031234567", "+447700900123"])
    email: str = Field(min_length=5, max_length=254)
    states_served: list[str] = Field(min_length=1, max_length=10, examples=[["Enugu", "Anambra"]])
    specialties: list[SpecialtyName] = Field(min_length=1, max_length=5)
    years_in_business: int = Field(ge=0, le=80)
    projects_completed: int = Field(ge=0, le=10_000)
    cac_rc_number: str | None = Field(default=None, min_length=3, max_length=30, examples=["RC1234567"])
    corbon_number: str | None = Field(default=None, min_length=3, max_length=40)
    reference_1_name: str = Field(min_length=2, max_length=200)
    reference_1_phone: str = Field(min_length=7, max_length=20)
    reference_2_name: str = Field(min_length=2, max_length=200)
    reference_2_phone: str = Field(min_length=7, max_length=20)
    # The applicant agrees to be contacted, to their references being called, and to appearing in
    # client shortlists.
    consent: Literal[True]
    # A field real people never see. Bots fill it in; we answer 201 and store nothing.
    website: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def _clean_lists(self) -> Self:
        states = [s.strip() for s in self.states_served]
        if any(len(s) < 2 or len(s) > 60 for s in states):
            raise ValueError("each state must be 2 to 60 characters")
        self.states_served = list(dict.fromkeys(states))  # no repeats, order kept
        self.specialties = list(dict.fromkeys(self.specialties))
        return self


class ContractorApplicationCreated(BaseModel):
    id: uuid.UUID
    status: Literal["pending"]


class ContractorApplicationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_name: str
    contact_name: str
    states_served: list[str]
    specialties: list[str]
    status: str
    created_at: datetime


class ContractorApplicationOut(ContractorApplicationListItem):
    """One application in full, for ops to check before deciding."""

    phone: str
    email: str
    years_in_business: int
    projects_completed: int
    cac_rc_number: str | None
    corbon_number: str | None
    reference_1_name: str
    reference_1_phone: str
    reference_2_name: str
    reference_2_phone: str
    registration_verified: bool
    reference_1_verified: bool
    reference_2_verified: bool
    ops_notes: str | None
    rejection_reason: str | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    consented_at: datetime
    updated_at: datetime


class ContractorDecisionIn(BaseModel):
    """Ops' decision. Approval needs both references ticked (and the registration when a number was given) and
    a profile summary ops write themselves; rejection needs a reason."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: Literal["approved", "rejected"]
    registration_verified: bool = False
    reference_1_verified: bool = False
    reference_2_verified: bool = False
    notes: str | None = Field(default=None, max_length=2000)  # what ops looked at, for the record
    summary: str | None = Field(default=None, max_length=1000)  # the profile text clients will read
    reason: str | None = Field(default=None, max_length=1000)  # why, when rejecting

    @model_validator(mode="after")
    def _needs(self) -> Self:
        if self.decision == "rejected" and not (self.reason and self.reason.strip()):
            raise ValueError("a reason is required when rejecting")
        if self.decision == "approved" and not (self.summary and len(self.summary.strip()) >= 20):
            raise ValueError("a profile summary of at least 20 characters is required when approving")
        return self


class ContractorOut(BaseModel):
    """A directory entry (ops only in phase 1; phase 2 builds the client-safe card from it)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str
    contact_name: str
    summary: str
    states_served: list[str]
    specialties: list[str]
    years_in_business: int
    projects_completed: int
    vetting_status: str
    listed: bool
    vetted_at: datetime


class ContractorApplicationPage(BaseModel):
    items: list[ContractorApplicationListItem]
    next_cursor: str | None


class ContractorPage(BaseModel):
    items: list[ContractorOut]
    next_cursor: str | None


# --- Match requests (ADR 0007, phase 2) ---------------------------------------------------------------


class MatchRequestIn(BaseModel):
    """The client's brief. The budget and currency come from the project, not from here."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    state: str = Field(min_length=2, max_length=60, examples=["Enugu"])
    city: str = Field(min_length=2, max_length=80, examples=["Enugu"])
    work_type: SpecialtyName
    timeline: str = Field(min_length=2, max_length=200, examples=["Start within three months"])
    notes: str | None = Field(default=None, max_length=2000)


class ContractorCard(BaseModel):
    """What a client may see of a shortlisted contractor: never a phone number or an email address."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_name: str
    summary: str
    states_served: list[str]
    specialties: list[str]
    years_in_business: int
    projects_completed: int
    vetted_by_ibackhome: bool = True


class MatchRequestOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    state: str
    city: str
    work_type: str
    timeline: str
    notes: str | None
    budget_minor: int
    currency: str
    created_at: datetime
    decided_at: datetime | None
    cancel_reason: str | None
    shortlist: list[ContractorCard]  # in the order ops chose; empty until shortlisted
    chosen: ContractorCard | None  # set once the client has chosen


class MatchRequestOpsItem(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_title: str
    client_id: uuid.UUID
    status: str
    state: str
    city: str
    work_type: str
    timeline: str
    notes: str | None
    budget_minor: int
    currency: str
    created_at: datetime
    shortlist_count: int


class MatchRequestPage(BaseModel):
    items: list[MatchRequestOpsItem]
    next_cursor: str | None


class MatchShortlistIn(BaseModel):
    """1 to 3 contractor profile ids, in the order ops want the client to see them."""

    model_config = ConfigDict(extra="forbid")

    contractor_ids: list[uuid.UUID] = Field(min_length=1, max_length=3)
    note: str | None = Field(default=None, max_length=1000)  # for ops only

    @model_validator(mode="after")
    def _no_repeats(self) -> Self:
        if len(set(self.contractor_ids)) != len(self.contractor_ids):
            raise ValueError("each contractor can be on the shortlist once")
        return self


class MatchChooseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contractor_id: uuid.UUID  # a contractor profile id from the shortlist


class MatchCancelIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str | None = Field(default=None, max_length=500)
