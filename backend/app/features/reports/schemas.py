"""Response shapes for weekly reports. Owner: James."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ReportOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    week_start: date
    status: str
    body_md: str
    evidence_ids: list[uuid.UUID]
    pdf_url: str | None  # a 15-minute link, once the report has been reviewed
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
