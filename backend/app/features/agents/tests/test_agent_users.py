"""Agent identities, their seeded ops users, and service tokens through the real sign-in check."""

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.core.config import get_settings
from app.features.agents import service
from app.features.projects import service as projects
from app.features.projects.schemas import ProjectCreate
from scripts import seed

READ_PROJECT = "GET /api/v1/projects/{project_id}"


def test_each_agent_has_a_fixed_distinct_user_id() -> None:
    ids = [service.agent_user_id(name) for name in service.AGENTS]

    assert ids == [service.agent_user_id(name) for name in service.AGENTS]  # same every time
    assert len(set(ids)) == len(service.AGENTS)


def test_agent_email_can_never_receive_a_login_code() -> None:
    assert service.agent_email("quote_checker") == "quote-checker.agent@ibackhome.invalid"


async def test_seed_creates_one_active_ops_user_per_agent_idempotently(db_session: AsyncSession) -> None:
    first = [await seed.upsert_agent_user(db_session, name) for name in service.AGENTS]
    again = [await seed.upsert_agent_user(db_session, name) for name in service.AGENTS]

    assert (
        [u.id for u in first] == [u.id for u in again] == [service.agent_user_id(n) for n in service.AGENTS]
    )
    assert all((u.role, u.status) == ("ops", "active") for u in again)
    assert again[0].email == service.agent_email("report")


def test_seed_refuses_to_run_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "environment", "production")

    with pytest.raises(SystemExit, match="production"):
        seed.refuse_production()


async def agent_and_project(session: AsyncSession) -> tuple[User, str]:
    agent = await seed.upsert_agent_user(session, "report")
    client = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role="client", status="active")
    session.add(client)
    await session.flush()
    data = ProjectCreate(
        title="Bungalow", address="2 Abakpa Road, Enugu", currency="NGN", budget_minor=10_000
    )
    project = await projects.create_project(session, client, data)
    return agent, str(project.id)


def bearer_for(agent: User, *routes: str) -> dict[str, str]:
    token = service.create_service_token("report", routes, user_id=agent.id)
    return {"Authorization": f"Bearer {token}"}


async def test_agent_reads_a_route_on_its_list(client: AsyncClient, db_session: AsyncSession) -> None:
    agent, project_id = await agent_and_project(db_session)

    response = await client.get(f"/api/v1/projects/{project_id}", headers=bearer_for(agent, READ_PROJECT))

    assert response.status_code == 200
    assert response.json()["id"] == project_id


async def test_agent_gets_403_off_its_list(client: AsyncClient, db_session: AsyncSession) -> None:
    agent, project_id = await agent_and_project(db_session)

    response = await client.get(f"/api/v1/projects/{project_id}/boq", headers=bearer_for(agent, READ_PROJECT))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "route_not_allowed"


async def test_agent_gets_403_on_the_boq_approve_route(client: AsyncClient, db_session: AsyncSession) -> None:
    # The approve route exists on main; it can't be listed, so any agent token is refused there.
    agent, project_id = await agent_and_project(db_session)

    response = await client.post(
        f"/api/v1/projects/{project_id}/boq/approve", headers=bearer_for(agent, READ_PROJECT)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "route_not_allowed"


async def test_suspended_agent_user_is_refused(client: AsyncClient, db_session: AsyncSession) -> None:
    agent, project_id = await agent_and_project(db_session)
    agent.status = "suspended"
    await db_session.flush()

    response = await client.get(f"/api/v1/projects/{project_id}", headers=bearer_for(agent, READ_PROJECT))

    assert response.status_code == 403
