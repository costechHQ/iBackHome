"""Request and response shapes for the ops console. Owner: Abigail."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VettingItem(BaseModel):
    """A supervisor application waiting for ops (decide it with POST /supervisors/{id}/vetting)."""

    user_id: uuid.UUID
    registration_body: str
    registration_no: str
    submitted_at: datetime


class FlaggedEvidenceItem(BaseModel):
    """A capture the server flagged (decide it with POST /evidence/{id}/decision)."""

    evidence_id: uuid.UUID
    project_id: uuid.UUID
    kind: str
    captured_by: uuid.UUID
    captured_at: datetime
    reason: str | None
    flagged_at: datetime


class DisputeItem(BaseModel):
    """A milestone dispute that is still open."""

    dispute_id: uuid.UUID
    project_id: uuid.UUID
    milestone_id: uuid.UUID
    reason: str
    opened_at: datetime
    proposed_outcome: str | None = Field(
        default=None,
        description="The first ops approval's outcome (release or rework); a different ops user confirms it",
    )
    proposed_by: uuid.UUID | None = Field(default=None, description="The ops user who proposed it")
    proposed_at: datetime | None = None


class OpsQueue(BaseModel):
    """Everything waiting for ops in one place, oldest first."""

    vetting: list[VettingItem]
    flagged_evidence: list[FlaggedEvidenceItem]
    disputes: list[DisputeItem]
