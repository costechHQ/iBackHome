"""Test helpers for projects: real users with real access tokens, projects and a site polygon."""

import secrets
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.users import service as users
from app.base.users.models import User
from app.features.projects import service
from app.features.projects.models import Project
from app.features.projects.schemas import ProjectCreate
from app.features.supervision import service as supervision
from app.features.supervision.schemas import DeclaredRelation, SupervisorApplication, VettingDecision

# About 88 m x 78 m in Independence Layout, Enugu, [lon, lat] as GeoJSON wants.
FENCE: dict[str, Any] = {
    "type": "Polygon",
    "coordinates": [
        [[7.5135, 6.4480], [7.5143, 6.4480], [7.5143, 6.4487], [7.5135, 6.4487], [7.5135, 6.4480]]
    ],
}
INSIDE = {"lat": 6.4483, "lon": 7.5139}
OUTSIDE = {"lat": 6.4500, "lon": 7.5139}  # about 150 m north


def random_phone() -> str:
    return f"+234803{secrets.randbelow(10**7):07d}"


async def make_user(
    session: AsyncSession, role: str, *, status: str = "active", phone: str | None = None
) -> User:
    user = User(phone=phone or random_phone(), role=role, status=status)
    session.add(user)
    await session.flush()
    return user


def bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {users.create_access_token(user)}"}


def project_data(**overrides: Any) -> ProjectCreate:
    fields: dict[str, Any] = {
        "title": "4-bedroom duplex",
        "address": "12 Chime Avenue, Enugu",
        "currency": "NGN",
        "budget_minor": 45_000_000_00,
    }
    return ProjectCreate(**(fields | overrides))


async def make_project(
    session: AsyncSession,
    *,
    client: User | None = None,
    contractor: User | None = None,
    supervisor: User | None = None,
) -> Project:
    """A draft project. The supervisor is set directly here; set_supervisor() has its own tests."""
    client = client or await make_user(session, "client")
    data = project_data(contractor_phone=contractor.phone if contractor else None)
    project = await service.create_project(session, client, data)
    if supervisor is not None:
        project.supervisor_id = supervisor.id
        await session.flush()
    return project


async def make_vetted_supervisor(session: AsyncSession, *, related_to: str | None = None) -> User:
    """A supervisor approved by ops through James's service, optionally related to a contractor's phone."""
    supervisor = await make_user(session, "supervisor")
    relations = [DeclaredRelation(contractor_phone=related_to, relationship="brother")] if related_to else []
    await supervision.submit_application(
        session,
        supervisor.id,
        SupervisorApplication(
            registration_body="COREN",
            registration_no="R12345",
            guarantor_1="Ngozi Eze, +2348031234567",
            guarantor_2="Emeka Obi, +2348037654321",
            related_contractors=relations,
        ),
    )
    ops = await make_user(session, "ops")
    await supervision.vet(
        session,
        supervisor.id,
        VettingDecision(
            decision="approved",
            registration_verified=True,
            nin_verified=True,
            guarantor_1_verified=True,
            guarantor_2_verified=True,
        ),
        ops.id,
    )
    return supervisor


async def audit_entries(session: AsyncSession, object_id: uuid.UUID) -> list[AuditEntry]:
    result = await session.scalars(
        select(AuditEntry).where(AuditEntry.object_id == object_id).order_by(AuditEntry.at, AuditEntry.id)
    )
    return list(result)
