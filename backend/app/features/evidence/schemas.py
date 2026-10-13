"""Request and response shapes for evidence."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
