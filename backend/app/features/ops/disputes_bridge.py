"""What the ops queue needs from Gabriel's disputes: the ones still open.

Gabriel's disputes (his Day 5) are not on main yet, and until they are there cannot be any open
dispute, so this honestly returns an empty list. When his code is merged, replace the body with a
call to his service (for example `escrow.list_open_disputes(session)`) and map it to `OpenDispute`.
Nothing else changes. Tests replace this function.
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
    return []
