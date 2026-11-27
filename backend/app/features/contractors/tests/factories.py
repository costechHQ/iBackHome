"""Builders shared by the contractor tests."""

import secrets
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.base.users.models import User
from app.features.contractors import applications
from app.features.contractors.models import ContractorApplication
from app.features.contractors.schemas import ContractorApplicationIn

URL = "/api/v1/contractor-applications"


def random_phone() -> str:
    return f"+234803{secrets.randbelow(10**7):07d}"


async def make_user(session: AsyncSession, role: str, phone: str | None = None) -> User:
    user = User(phone=phone or random_phone(), role=role, status="active")
    session.add(user)
    await session.flush()
    return user


def bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {users.create_access_token(user)}"}


def form(**changes: Any) -> dict[str, Any]:
    """A valid form with a phone and email no other test uses."""
    n = uuid.uuid4().int % 10_000_000
    body: dict[str, Any] = {
        "business_name": "Obi Building Works",
        "contact_name": "Chinedu Obi",
        "phone": f"0803{n:07d}",
        "email": f"Obi.{n}@Example.com",
        "states_served": ["Enugu", "Anambra"],
        "specialties": ["buildings", "roofing"],
        "years_in_business": 12,
        "projects_completed": 30,
        "cac_rc_number": "RC1234567",
        "corbon_number": None,
        "reference_1_name": "Emeka Obi",
        "reference_1_phone": f"0805{n:07d}",
        "reference_2_name": "Ada Nwosu",
        "reference_2_phone": f"0807{n:07d}",
        "consent": True,
    }
    body.update(changes)
    return body


async def make_application(session: AsyncSession, **changes: Any) -> ContractorApplication:
    """A saved, pending application (no HTTP)."""
    data = form(**changes)
    return await applications.submit(session, ContractorApplicationIn(**data), "127.0.0.1")


def approval(**changes: Any) -> dict[str, Any]:
    """An approving decision with every check ticked and a profile summary."""
    body: dict[str, Any] = {
        "decision": "approved",
        "registration_verified": True,
        "reference_1_verified": True,
        "reference_2_verified": True,
        "notes": "RC checked on the CAC register; both references called.",
        "summary": "Established Enugu builder with twelve years on residential buildings and roofing.",
    }
    body.update(changes)
    return body
