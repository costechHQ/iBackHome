"""What milestones need to know about a project.

Claim, verify and approve each need a few facts from Christopher's projects feature: the
project's status (it must be `active`) and who its client, contractor and assigned supervisor
are. This file is the one place that asks, through `projects.get_project()`.

Tests can replace `get_project_info` to try one rule at a time without building a full project.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects import service as projects


@dataclass(frozen=True)
class ProjectInfo:
    id: uuid.UUID
    status: str  # draft | boq_review | active | paused | completed
    contractor_id: uuid.UUID | None
    client_id: uuid.UUID | None = None
    supervisor_id: uuid.UUID | None = None


async def get_project_info(session: AsyncSession, project_id: uuid.UUID) -> ProjectInfo:
    """The project's status and people. 404 project_not_found."""
    project = await projects.get_project(session, project_id)
    return ProjectInfo(
        id=project.id,
        status=project.status,
        contractor_id=project.contractor_id,
        client_id=project.client_id,
        supervisor_id=project.supervisor_id,
    )
