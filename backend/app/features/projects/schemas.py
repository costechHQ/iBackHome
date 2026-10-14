"""Request and response shapes for projects and sites. Owner: Christopher."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Upper limit for any money amount here (10^15 kobo = N10 trillion); keeps sums inside BIGINT.
MAX_AMOUNT_MINOR = 10**15


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["4-bedroom duplex, Independence Layout"])
    address: str = Field(min_length=1, max_length=500, examples=["12 Chime Avenue, Enugu"])
    currency: str = Field(pattern=r"^[A-Z]{3}$", examples=["NGN"])
    # Integer minor units (kobo, cents); strict, so 100.0 is refused too. Never floats for money.
    budget_minor: int = Field(strict=True, gt=0, le=MAX_AMOUNT_MINOR, examples=[45_000_000_00])
    # Optional: the client can name the contractor later. Same phone rules as login.
    contractor_phone: str | None = Field(default=None, min_length=7, max_length=20, examples=["08031234567"])

    @field_validator("title", "address")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class Pin(BaseModel):
    lat: float = Field(ge=-90, le=90, examples=[6.4483])
    lon: float = Field(ge=-180, le=180, examples=[7.5139])


class SiteSet(BaseModel):
    location: Pin
    # GeoJSON Polygon (or a Feature holding one), [lon, lat] order, SRID 4326.
    geofence: dict[str, Any] = Field(
        examples=[
            {
                "type": "Polygon",
                "coordinates": [
                    [[7.5135, 6.4480], [7.5143, 6.4480], [7.5143, 6.4487], [7.5135, 6.4487], [7.5135, 6.4480]]
                ],
            }
        ]
    )


class SiteOut(BaseModel):
    location: Pin
    geofence: dict[str, Any]  # GeoJSON Polygon
    updated_at: datetime


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    contractor_id: uuid.UUID | None
    supervisor_id: uuid.UUID | None
    title: str
    address: str
    status: str
    currency: str
    budget_minor: int
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectOut):
    site: SiteOut | None


class ProjectPage(BaseModel):
    items: list[ProjectOut]
    next_cursor: str | None


# --- Bill of quantities -------------------------------------------------------------------------

MAX_LINES_PER_MILESTONE = 200
MAX_LINES = 500


class BoqLineIn(BaseModel):
    description: str = Field(min_length=1, max_length=500, examples=["Concrete 1:2:4 for strip foundation"])
    unit: str = Field(min_length=1, max_length=20, examples=["m3"])
    # Up to 3 decimal places; send it as a string ("2.5") or a number.
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3, examples=["12.5"])
    unit_price_minor: int = Field(strict=True, gt=0, le=10**13, examples=[9_500_000])
    # Optional: if sent, it must equal quantity x unit_price_minor rounded half-up.
    total_minor: int | None = Field(default=None, strict=True, gt=0)

    @field_validator("description", "unit")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class BoqMilestoneIn(BaseModel):
    name: str = Field(min_length=1, max_length=120, examples=["Foundation"])
    items: list[BoqLineIn] = Field(min_length=1, max_length=MAX_LINES_PER_MILESTONE)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class BoqSubmit(BaseModel):
    """The whole BoQ, milestones in build order. Submitting again replaces it."""

    milestones: list[BoqMilestoneIn] = Field(min_length=1)


class BoqLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    line_no: int
    description: str
    unit: str
    quantity: Decimal
    unit_price_minor: int
    total_minor: int


class BoqMilestoneOut(BaseModel):
    sequence: int
    name: str
    amount_minor: int
    milestone_id: uuid.UUID | None  # set once the BoQ is approved
    items: list[BoqLineOut]


class BoqApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    user_id: uuid.UUID
    approved_at: datetime


class BoqOut(BaseModel):
    project_id: uuid.UUID
    project_status: str
    currency: str
    budget_minor: int
    boq_total_minor: int  # may be above the budget: the client sees both before approving
    milestones: list[BoqMilestoneOut]
    approvals: list[BoqApprovalOut]
    approvals_missing: list[str]  # roles still to approve: client, contractor, ops
