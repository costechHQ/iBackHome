"""Request and response shapes for evidence."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class DeviceIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    public_key: str = Field(min_length=1, max_length=512)


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    device_id: str
    public_key: str
    registered_at: datetime
    revoked_at: datetime | None


class UploadUrlRequest(BaseModel):
    project_id: uuid.UUID
    kind: Literal["photo", "video"]
    content_type: Literal["image/jpeg", "video/mp4"]


class UploadUrlOut(BaseModel):
    storage_key: str
    upload_url: str
    method: str = "PUT"
    headers: dict[str, str]
    expires_in: int
    max_bytes: int


class EvidenceIn(BaseModel):
    project_id: uuid.UUID
    milestone_id: uuid.UUID | None = None
    kind: Literal["photo", "video"]
    storage_key: str = Field(min_length=1, max_length=300)
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    captured_at: AwareDatetime
    gps_time: AwareDatetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0)
    device_id: str = Field(min_length=1, max_length=128)
    signature: str = Field(min_length=1, max_length=512)


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    milestone_id: uuid.UUID | None
    captured_by: uuid.UUID
    captured_by_role: str
    kind: str
    storage_key: str
    content_type: str
    size_bytes: int
    file_sha256: str
    captured_at: datetime
    gps_time: datetime
    latitude: float
    longitude: float
    accuracy_m: float
    device_id: str
    status: str
    reject_reason: str | None
    created_at: datetime


class GalleryItem(EvidenceOut):
    """A capture plus a short-lived link to view it (clients get an EXIF-stripped copy)."""

    read_url: str
    read_url_expires_in: int
    is_client_copy: bool


class GalleryPage(BaseModel):
    items: list[GalleryItem]
    next_cursor: str | None


class DecisionIn(BaseModel):
    decision: Literal["accepted", "rejected"]
    notes: str = Field(default="", max_length=1000)
