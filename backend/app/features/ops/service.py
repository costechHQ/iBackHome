"""Business rules for the ops console: the one queue of things waiting for ops. Owner: Abigail.

The queue owns no data. Each list is read through the owner's service, never from its tables:
vetting requests (supervision), flagged evidence (evidence) and open disputes (escrow, via a bridge
until Gabriel's disputes are merged).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.evidence import service as evidence
from app.features.ops import disputes_bridge
from app.features.ops.schemas import DisputeItem, FlaggedEvidenceItem, OpsQueue, VettingItem
from app.features.supervision import service as supervision

DEFAULT_LIMIT = 100


async def get_queue(session: AsyncSession, limit: int = DEFAULT_LIMIT) -> OpsQueue:
    """The three lists ops work through, each oldest first and capped at `limit`."""
    vetting = (await supervision.list_pending_vetting(session))[:limit]
    flagged = await evidence.list_flagged(session, limit)
    disputes = await disputes_bridge.list_open(session, limit)
    return OpsQueue(
        vetting=[
            VettingItem(
                user_id=p.user_id,
                registration_body=p.registration_body,
                registration_no=p.registration_no,
                submitted_at=p.created_at,
            )
            for p in vetting
        ],
        flagged_evidence=[
            FlaggedEvidenceItem(
                evidence_id=e.id,
                project_id=e.project_id,
                kind=e.kind,
                captured_by=e.captured_by,
                captured_at=e.captured_at,
                reason=e.reject_reason,
                flagged_at=e.updated_at,
            )
            for e in flagged
        ],
        disputes=[
            DisputeItem(
                dispute_id=d.id,
                project_id=d.project_id,
                milestone_id=d.milestone_id,
                reason=d.reason,
                opened_at=d.created_at,
                proposed_outcome=d.proposed_outcome,
                proposed_by=d.proposed_by,
                proposed_at=d.proposed_at,
            )
            for d in disputes
        ],
    )
