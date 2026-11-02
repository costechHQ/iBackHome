"""Response shapes for weekly reports. Owner: James."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

MAX_NOTE_CHARS = 2000


class PersonRef(BaseModel):
    """A person named on a report: the id and name only (no phone or email)."""

    id: uuid.UUID
    full_name: str | None


class ReportOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    week_start: date
    status: str
    body_md: str  # AI-generated; the reviewer's own words are in `supervisor_note`, never in here
    supervisor_note: str | None
    note_by: PersonRef | None  # who wrote the note: it is shown under their name
    reviewed_by: PersonRef | None  # who marked it reviewed: "Reviewed by <name>"
    evidence_ids: list[uuid.UUID]
    pdf_url: str | None  # a 15-minute link, once the report has been reviewed
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReportNoteIn(BaseModel):
    """The note to the client. An empty or blank note removes it."""

    supervisor_note: str | None = Field(default=None, max_length=MAX_NOTE_CHARS)
