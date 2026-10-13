"""What milestones need to know about a project.

Claiming a milestone needs two facts from Christopher's projects feature: the project's
status (it must be `active`) and who its contractor is. This file is the one place that asks.

Until Christopher's `projects` feature is merged (backend day 3), `get_project_info` refuses
with 503 `projects_not_ready`, so a claim can never skip the checks. Tests replace it.
When his code is in main, replace the body with a call to his service
(see docs/api-guide.md, "Connecting projects"). Nothing else changes.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError


@dataclass(frozen=True)
class ProjectInfo:
    id: uuid.UUID
    status: str  # draft | boq_review | active | paused | completed
    contractor_id: uuid.UUID | None


async def get_project_info(session: AsyncSession, project_id: uuid.UUID) -> ProjectInfo:
    raise AppError("projects_not_ready", "Projects are not connected yet.", 503)
