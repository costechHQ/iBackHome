"""Which evidence counts toward verifying a milestone.

Verify asks Abigail's evidence feature for the milestone's accepted supervisor photos
(`evidence.accepted_for_milestone()`): accepted after every server check, and captured by the
supervisor. Contractor uploads and pending, flagged or rejected photos never count.
Tests replace `accepted_evidence_ids` directly.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.evidence import service as evidence


async def accepted_evidence_ids(session: AsyncSession, milestone_id: uuid.UUID) -> set[uuid.UUID]:
    """IDs of this milestone's evidence that is accepted and was captured by the supervisor."""
    return {item.id for item in await evidence.accepted_for_milestone(session, milestone_id)}
