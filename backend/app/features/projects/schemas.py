"""Request and response shapes for projects and sites. Owner: Christopher."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["4-bedroom duplex, Independence Layout"])
    address: str = Field(min_length=1, max_length=500, examples=["12 Chime Avenue, Enugu"])
    currency: str = Field(pattern=r"^[A-Z]{3}$", examples=["NGN"])
    # Integer minor units (kobo, cents); strict, so 100.0 is refused too. Never floats for money.
    budget_minor: int = Field(strict=True, gt=0, le=10**15, examples=[45_000_000_00])
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
