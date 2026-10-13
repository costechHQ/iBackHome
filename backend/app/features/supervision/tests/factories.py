"""Builders shared by the supervision tests."""

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.base.users.models import User
from app.features.supervision.schemas import DeclaredRelation, SupervisorApplication, VettingDecision

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
