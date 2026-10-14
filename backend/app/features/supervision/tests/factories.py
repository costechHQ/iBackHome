"""Builders shared by the supervision tests."""

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.base.users.models import User
from app.features.projects import service as projects
from app.features.projects.models import Project
from app.features.projects.schemas import ProjectCreate
from app.features.supervision import service
from app.features.supervision.schemas import DeclaredRelation, SupervisorApplication, VettingDecision

# The contractor on the `project` fixture; supervisors who declare this number are related to them.
CONTRACTOR_PHONE = "+2348012345678"

ALL_CHECKS = {
    "registration_verified": True,
    "nin_verified": True,
    "guarantor_1_verified": True,
    "guarantor_2_verified": True,
}


def random_phone() -> str:
    return f"+234803{secrets.randbelow(10**7):07d}"


async def make_user(session: AsyncSession, role: str, phone: str | None = None) -> User:
    user = User(phone=phone or random_phone(), role=role, status="active")
    session.add(user)
    await session.flush()
    return user


def application(*relations: DeclaredRelation) -> SupervisorApplication:
    return SupervisorApplication(
        registration_body="COREN",
        registration_no="R.12345",
        guarantor_1="Ngozi Eze, +2348031234567",
        guarantor_2="Emeka Obi, +2348039876543",
        related_contractors=list(relations),
    )


def approval() -> VettingDecision:
    return VettingDecision.model_validate({"decision": "approved", **ALL_CHECKS})


def bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {users.create_access_token(user)}"}


async def make_vetted(session: AsyncSession, ops: User, *relations: DeclaredRelation) -> User:
    """A supervisor ops has approved, optionally with declared relatives."""
    user = await make_user(session, "supervisor")
    await service.submit_application(session, user.id, application(*relations))
    await service.vet(session, user.id, approval(), ops.id)
    return user


async def make_project(session: AsyncSession, *, contractor_phone: str | None = None) -> Project:
    """A draft project created through Christopher's projects.create_project(), by a new client."""
    client = await make_user(session, "client")
    data = ProjectCreate(
        title="3-bedroom bungalow",
        address="5 Zik Avenue, Enugu",
        currency="NGN",
        budget_minor=30_000_000_00,
        contractor_phone=contractor_phone,
    )
    return await projects.create_project(session, client, data)
