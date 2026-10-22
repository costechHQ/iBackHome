"""Fill a fresh database with test data. Owner: James.

v1 (backend Day 2): one user per role, with the supervisor already vetted.
v2 (backend Day 3): a second vetted supervisor, and two Enugu projects with sites, geofences and
                    a supervisor each. Projects stay in `draft` (the BoQ comes from the simulator).
v3 (backend Day 5): one active `ops` user per AI agent (agents.service.AGENTS), with the fixed id
                    agents.service.agent_user_id() so each agent can sign in with its service token.
v4 (backend gate):  a verified supplier owned by the seeded supplier user, and Paystack bank accounts
                    (payout recipients) for the contractor and that supplier, so milestone payouts and
                    supplier payments can run. With PAYSTACK_SECRET_KEY set (test mode) they are
                    registered with Paystack; on ENVIRONMENT=local without a key a stand-in recipient
                    code is used; elsewhere without a key they are skipped (and said so).
v5 (web W3):        a second human ops user, because resolving a dispute needs two different ops users
                    (escrow.resolve_dispute); the agent ops users can't sign in with a code.
v6 (web W5b):       the seeded people have agreed to the current terms and privacy policy (NDPA consent,
                    users.record_consent), so the web portals don't stop them at the consent card.

Refuses to run when ENVIRONMENT=production.

Run from backend/ after `uv run alembic upgrade head` (or inside the api container):

    uv run python scripts/seed.py

Safe to run twice: users are matched by phone (or email) and projects by title, so nothing is
duplicated. Everything goes through each owner's service, so their rules and audit entries apply.
Sign in with an OTP to the phone or email below; locally the code is printed in the API log.
The numbers are made up but valid, because login refuses invalid numbers.
"""

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports when run as a script

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.base.payments import register_payout_recipient  # noqa: E402
from app.base.payments.paystack import PaystackClient, RecipientResult, get_paystack_client  # noqa: E402
from app.base.payments.settings import get_payments_settings  # noqa: E402
from app.base.users import service as users  # noqa: E402
from app.base.users.models import Role, User, UserStatus  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.features.agents import service as agents  # noqa: E402
from app.features.projects import service as projects  # noqa: E402
from app.features.projects.models import Project  # noqa: E402
from app.features.projects.schemas import Pin, ProjectCreate, SiteSet  # noqa: E402
from app.features.supervision import service as supervision  # noqa: E402
from app.features.supervision.schemas import SupervisorApplication, VettingDecision  # noqa: E402
from app.features.suppliers import service as suppliers  # noqa: E402
from app.features.suppliers.models import Supplier  # noqa: E402


@dataclass(frozen=True)
class SeedUser:
    key: str
    role: Role
    full_name: str
    phone: str | None
    email: str | None
    country: str
    timezone: str


# The client lives abroad and signs in by email (spec: login); everyone else by Nigerian phone.
USERS = [
    SeedUser(
        "client", Role.CLIENT, "Adaeze Okafor", None, "adaeze.client@example.com", "GB", "Europe/London"
    ),
    SeedUser(
        "contractor", Role.CONTRACTOR, "Chukwuemeka Nwosu", "+2348030000001", None, "NG", "Africa/Lagos"
    ),
    SeedUser("supervisor", Role.SUPERVISOR, "Ifeoma Eze", "+2348030000002", None, "NG", "Africa/Lagos"),
    SeedUser("supervisor_2", Role.SUPERVISOR, "Nnamdi Okeke", "+2348030000005", None, "NG", "Africa/Lagos"),
    SeedUser(
        "supplier", Role.SUPPLIER, "Obinna Building Materials", "+2348030000003", None, "NG", "Africa/Lagos"
    ),
    SeedUser("ops", Role.OPS, "Chiamaka Ops", "+2348030000004", "ops@example.com", "NG", "Africa/Lagos"),
    # A dispute is resolved by two different ops users: one proposes, the other confirms.
    SeedUser("ops_2", Role.OPS, "Obiora Ops", "+2348030000006", "ops2@example.com", "NG", "Africa/Lagos"),
]


def square_fence(lat: float, lon: float, half_side_deg: float = 0.0004) -> dict[str, Any]:
    """A GeoJSON square around the pin, about 90 m a side in Enugu. [lon, lat] order."""
    s, w, n, e = lat - half_side_deg, lon - half_side_deg, lat + half_side_deg, lon + half_side_deg
    return {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}


@dataclass(frozen=True)
class SeedProject:
    title: str
    address: str
    budget_minor: int  # kobo
    lat: float
    lon: float
    supervisor: str  # key in USERS


PROJECTS = [
    SeedProject(
        "4-bedroom duplex, Independence Layout",
        "14 Chime Avenue, Independence Layout, Enugu",
        45_000_000_00,
        6.4483,
        7.5139,
        "supervisor",
    ),
    SeedProject(
        "3-bedroom bungalow, Trans-Ekulu",
        "7 Ekulu Close, Trans-Ekulu, Enugu",
        28_500_000_00,
        6.4805,
        7.5208,
        "supervisor_2",
    ),
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
    # Agreed to the current terms and privacy policy (audited; does nothing if already agreed).
    settings = get_settings()
    await users.record_consent(session, user, settings.terms_version, settings.privacy_version)
    return user


async def upsert_agent_user(session: AsyncSession, agent_name: str) -> User:
    """The agent's own active ops user, at its fixed id. Its .invalid email can never get a login code."""
    user = await users.get_user(session, agents.agent_user_id(agent_name))
    if user is None:
        user = User(id=agents.agent_user_id(agent_name), email=agents.agent_email(agent_name))
        session.add(user)
    user.role = Role.OPS.value
    user.full_name = f"{agent_name.replace('_', ' ').capitalize()} agent"
    user.country = "NG"
    user.timezone = "Africa/Lagos"
    user.status = UserStatus.ACTIVE.value
    await session.flush()
    return user


async def vet_supervisor(session: AsyncSession, supervisor: User, ops: User, registration_no: str) -> None:
    if await supervision.is_vetted(session, supervisor.id):
        return
    await supervision.submit_application(
        session,
        supervisor.id,
        SupervisorApplication(
            registration_body="COREN",
            registration_no=registration_no,
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


async def upsert_project(session: AsyncSession, seed: SeedProject, users: dict[str, User]) -> Project:
    client, contractor = users["client"], users["contractor"]
    mine, _ = await projects.list_projects(session, client, limit=100)
    project = next((p for p in mine if p.title == seed.title), None)
    if project is None:
        project = await projects.create_project(
            session,
            client,
            ProjectCreate(
                title=seed.title,
                address=seed.address,
                currency="NGN",
                budget_minor=seed.budget_minor,
                contractor_phone=contractor.phone,
            ),
        )
    if await projects.get_site(session, project.id) is None:
        site = SiteSet(location=Pin(lat=seed.lat, lon=seed.lon), geofence=square_fence(seed.lat, seed.lon))
        await projects.set_site(session, client, project.id, site)
    # set_supervisor() does nothing if this supervisor is already on the project.
    await projects.set_supervisor(session, project.id, users[seed.supervisor].id, users["ops"].id)
    return project


SUPPLIER_NAME = "Obinna Building Materials"
SUPPLIER_ADDRESS = "Ogbete Main Market, Enugu"


@dataclass(frozen=True)
class SeedBankAccount:
    owner: str  # "contractor" or "supplier"
    account_name: str
    account_number: str  # test NUBAN: only sent to Paystack, never stored (we keep the last 4)
    bank_code: str


# Test-mode accounts (Paystack test keys never move real money). 057 = Zenith Bank.
BANK_ACCOUNTS = [
    SeedBankAccount("contractor", "Chukwuemeka Nwosu", "0123456789", "057"),
    SeedBankAccount("supplier", SUPPLIER_NAME, "0987654321", "057"),
]


class StandInPaystack:
    """ENVIRONMENT=local without PAYSTACK_SECRET_KEY: a fixed recipient code per account, so the
    rest of the seed (and local payout tests by hand) still works. Never used elsewhere."""

    async def create_transfer_recipient(
        self, account_name: str, account_number: str, bank_code: str
    ) -> RecipientResult:
        return RecipientResult(
            recipient_code=f"RCP_seed_{bank_code}_{account_number[-4:]}",
            bank_code=bank_code,
            bank_name="Zenith Bank (seed)",
            account_name=account_name,
            account_last4=account_number[-4:],
        )

    async def initiate_transfer(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("the stand-in only registers recipients")

    async def verify_transfer(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("the stand-in only registers recipients")


def paystack_for_seed() -> PaystackClient | None:
    """Real Paystack when a key is set; the stand-in locally; otherwise None (skip bank accounts)."""
    if get_payments_settings().paystack_secret_key:
        return get_paystack_client()
    if get_settings().environment == "local":
        return StandInPaystack()
    return None


async def upsert_supplier(session: AsyncSession, owner: User, ops: User) -> Supplier:
    return await suppliers.ensure_supplier(
        session, SUPPLIER_NAME, owner_id=owner.id, address=SUPPLIER_ADDRESS, verified=True, actor_id=ops.id
    )


async def register_bank_accounts(
    session: AsyncSession, people: dict[str, User], supplier: Supplier, paystack: PaystackClient | None
) -> list[str]:
    """Register each seed bank account; returns one line per account for the summary."""
    if paystack is None:
        return ["bank accounts skipped: set PAYSTACK_SECRET_KEY (test key) to register them"]
    lines = []
    for account in BANK_ACCOUNTS:
        is_contractor = account.owner == "contractor"
        try:
            recipient = await register_payout_recipient(
                session,
                account_name=account.account_name,
                account_number=account.account_number,
                bank_code=account.bank_code,
                actor_id=people["ops"].id,
                user_id=people["contractor"].id if is_contractor else None,
                supplier_id=None if is_contractor else supplier.id,
                client=paystack,
            )
        except AppError as exc:  # Paystack refused or is down: the rest of the seed still stands
            lines.append(f"bank account for {account.owner} not registered: {exc.code} ({exc.message})")
            continue
        masked = recipient.account_number_masked
        lines.append(f"bank        {account.owner:<11} {recipient.recipient_code} {masked}")
    return lines


def refuse_production() -> None:
    if get_settings().environment == "production":
        raise SystemExit("seed.py refuses to run with ENVIRONMENT=production: it creates test accounts.")


async def seed() -> None:
    refuse_production()
    async with SessionLocal() as session:
        people = {seed.key: await upsert_user(session, seed) for seed in USERS}
        await vet_supervisor(session, people["supervisor"], people["ops"], "SEED-0001")
        await vet_supervisor(session, people["supervisor_2"], people["ops"], "SEED-0002")
        seeded = [await upsert_project(session, seed, people) for seed in PROJECTS]
        agent_users = [await upsert_agent_user(session, name) for name in agents.AGENTS]
        supplier = await upsert_supplier(session, people["supplier"], people["ops"])
        bank_lines = await register_bank_accounts(session, people, supplier, paystack_for_seed())
        await session.commit()

    for user_seed in USERS:
        print(f"{user_seed.role.value:<11} {user_seed.full_name:<26} {user_seed.phone or user_seed.email}")
    for agent_user in agent_users:
        print(f"ops (agent) {agent_user.full_name:<26} {agent_user.id}")
    for project, project_seed in zip(seeded, PROJECTS, strict=True):
        print(f"project     {project.title:<40} supervisor: {people[project_seed.supervisor].full_name}")
    print(f"supplier    {supplier.name:<26} {supplier.id}")
    for line in bank_lines:
        print(line)


if __name__ == "__main__":
    if sys.platform == "win32":  # async psycopg can't use Windows' default event loop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed())
