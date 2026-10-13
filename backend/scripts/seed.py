"""Fill a fresh database with test data. Owner: James.

v1 (backend Day 2): one user per role, with the supervisor already vetted.
v2 (backend Day 3): two Enugu projects with sites and geofences (needs Christopher's projects).

Run from backend/ after `uv run alembic upgrade head` (or inside the api container):

    uv run python scripts/seed.py

Safe to run twice: users are matched by phone (or email), so nothing is duplicated.
Sign in with an OTP to the phone or email below; locally the code is printed in the API log.
The numbers are made up but valid, because login refuses invalid numbers.
"""

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports when run as a script

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.base.users.models import Role, User, UserStatus  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.features.supervision import service as supervision  # noqa: E402
from app.features.supervision.schemas import SupervisorApplication, VettingDecision  # noqa: E402


@dataclass(frozen=True)
class SeedUser:
    role: Role
    full_name: str
    phone: str | None
    email: str | None
    country: str
    timezone: str


# The client lives abroad and signs in by email (spec: login); everyone else by Nigerian phone.
USERS = [
    SeedUser(Role.CLIENT, "Adaeze Okafor", None, "adaeze.client@example.com", "GB", "Europe/London"),
    SeedUser(Role.CONTRACTOR, "Chukwuemeka Nwosu", "+2348030000001", None, "NG", "Africa/Lagos"),
    SeedUser(Role.SUPERVISOR, "Ifeoma Eze", "+2348030000002", None, "NG", "Africa/Lagos"),
    SeedUser(Role.SUPPLIER, "Obinna Building Materials", "+2348030000003", None, "NG", "Africa/Lagos"),
    SeedUser(Role.OPS, "Chiamaka Ops", "+2348030000004", "ops@example.com", "NG", "Africa/Lagos"),
]


async def upsert_user(session: AsyncSession, seed: SeedUser) -> User:
    match = User.phone == seed.phone if seed.phone else User.email == seed.email
    user = await session.scalar(select(User).where(match))
    if user is None:
        user = User(phone=seed.phone, email=seed.email)
        session.add(user)
    user.role = seed.role.value
    user.full_name = seed.full_name
    user.country = seed.country
    user.timezone = seed.timezone
    user.status = UserStatus.ACTIVE.value
    await session.flush()
    return user


async def vet_supervisor(session: AsyncSession, supervisor: User, ops: User) -> None:
    if await supervision.is_vetted(session, supervisor.id):
        return
    await supervision.submit_application(
        session,
        supervisor.id,
        SupervisorApplication(
            registration_body="COREN",
            registration_no="SEED-0001",
            guarantor_1="Ngozi Eze, +2348030000101",
            guarantor_2="Emeka Obi, +2348030000102",
        ),
    )
    decision = VettingDecision(
        decision="approved",
        registration_verified=True,
        nin_verified=True,
        guarantor_1_verified=True,
        guarantor_2_verified=True,
    )
    await supervision.vet(session, supervisor.id, decision, ops.id)


async def seed() -> None:
    async with SessionLocal() as session:
        users = {seed.role: await upsert_user(session, seed) for seed in USERS}
        await vet_supervisor(session, users[Role.SUPERVISOR], users[Role.OPS])
        await session.commit()
    for seed in USERS:
        print(f"{seed.role.value:<11} {seed.full_name:<26} {seed.phone or seed.email}")


if __name__ == "__main__":
    if sys.platform == "win32":  # async psycopg can't use Windows' default event loop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed())
