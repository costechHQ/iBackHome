"""Test helpers for milestones: real users with real tokens, and an active project with milestones."""

import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.users import service as users
from app.base.users.models import User
from app.features.milestones import service
from app.features.milestones.models import Milestone, MilestoneStatus
from app.features.milestones.schemas import MilestoneGroup
from app.features.projects import service as projects
from app.features.projects.models import Project
from app.features.projects.schemas import ProjectCreate


async def make_user(session: AsyncSession, role: str) -> User:
    user = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role=role, status="active")
    session.add(user)
    await session.flush()
    return user


def bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {users.create_access_token(user)}"}


async def make_project(
    session: AsyncSession,
    *,
    client: User | None = None,
    contractor: User | None = None,
    status: str = "active",
) -> Project:
    """A real project through projects.service (milestones.project_id must point at one)."""
    client = client or await make_user(session, "client")
    project = await projects.create_project(
        session,
        client,
        ProjectCreate(
            title="4-bedroom bungalow",
            address="Independence Layout, Enugu",
            currency="NGN",
            budget_minor=40_000_000_00,
            contractor_phone=contractor.phone if contractor else None,
        ),
    )
    project.status = status
    await session.flush()
    return project


@dataclass
class Site:
    """An active project, its people and its milestones (1: Foundation, 2: Roofing)."""

    project_id: uuid.UUID
    client: User
    contractor: User
    supervisor: User
    ops: User
    milestones: list[Milestone]


async def active_project(
    session: AsyncSession, *, first_status: MilestoneStatus = MilestoneStatus.CLAIMED
) -> Site:
    """A real project made through projects.service, set active with a supervisor assigned.

    The BoQ approval flow (Christopher's, tested there) is skipped: the project is made active
    directly and its milestones created with create_for_project(), as that flow would.
    """
    client = await make_user(session, "client")
    contractor = await make_user(session, "contractor")
    supervisor = await make_user(session, "supervisor")
    ops = await make_user(session, "ops")
    project = await make_project(session, client=client, contractor=contractor)
    project.supervisor_id = supervisor.id
    await session.flush()
    milestones = await service.create_for_project(
        session,
        project.id,
        [
            MilestoneGroup(name="Foundation", amount_minor=8_000_000_00),
            MilestoneGroup(name="Roofing", amount_minor=6_000_000_00),
        ],
        "NGN",
    )
    milestones[0].status = first_status
    await session.flush()
    return Site(project.id, client, contractor, supervisor, ops, milestones)


async def set_project_status(session: AsyncSession, project_id: uuid.UUID, status: str) -> None:
    project = await projects.get_project(session, project_id)
    project.status = status
    await session.flush()


async def audit_actions(session: AsyncSession, object_id: uuid.UUID) -> list[str]:
    rows = await session.scalars(
        select(AuditEntry.action).where(AuditEntry.object_id == object_id).order_by(AuditEntry.at)
    )
    return list(rows)
