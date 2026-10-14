"""Request and response shapes (Pydantic) for audit."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    object_type: str
    object_id: uuid.UUID
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    ip: str | None
    device_id: str | None
    at: datetime


class AuditPage(BaseModel):
    items: list[AuditEntryOut]
    next_cursor: str | None
