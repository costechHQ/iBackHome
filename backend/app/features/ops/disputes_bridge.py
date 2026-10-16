"""What the ops queue needs from Gabriel's disputes: the ones still open.

Reads `escrow.list_open_disputes(session, limit)` (oldest first) and keeps only what the queue
shows. Tests replace this function.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class OpenDispute:
    id: uuid.UUID
    project_id: uuid.UUID
    milestone_id: uuid.UUID
    reason: str
    created_at: datetime


async def list_open(session: AsyncSession, limit: int) -> list[OpenDispute]:
    # Imported here so ops never loads escrow at import time (escrow imports suppliers and projects).
    from app.features.escrow import service as escrow

    return [
        OpenDispute(
            id=d.id,
            project_id=d.project_id,
            milestone_id=d.milestone_id,
            reason=d.reason,
            created_at=d.created_at,
        )
        for d in await escrow.list_open_disputes(session, limit)
    ]
