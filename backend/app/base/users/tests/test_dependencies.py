"""current_user and require_role, the dependencies every other module uses."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service
from app.base.users.models import User
from app.base.users.tests.conftest import make_user
from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import register_error_handlers
from app.features.agents import service as agents

OpsUser = Annotated[User, Depends(service.require_role("ops"))]


def build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/anyone")
    async def anyone(user: service.CurrentUserDep) -> dict[str, str]:
        return {"id": str(user.id), "role": user.role}

    @app.get("/ops-only")
    async def ops_only(user: OpsUser) -> dict[str, str]:
        return {"role": user.role}

    @app.post("/milestones/{milestone_id}/release")
    async def release(milestone_id: str, user: OpsUser) -> dict[str, str]:
        return {"released": milestone_id}  # pragma: no cover - no agent may reach it

    return app


@pytest.fixture
async def http(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app = build_app()

    async def _session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _assert_401(response_coro: object) -> None:
    response = await response_coro  # type: ignore[misc]
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "unauthorized"


async def test_signed_in_user_gets_through(http: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, role="contractor")
    response = await http.get("/anyone", headers=_bearer(service.create_access_token(user)))
    assert response.status_code == 200
    assert response.json() == {"id": str(user.id), "role": "contractor"}


async def test_missing_token_is_401(http: AsyncClient) -> None:
    await _assert_401(http.get("/anyone"))


async def test_wrong_scheme_is_401(http: AsyncClient) -> None:
    await _assert_401(http.get("/anyone", headers={"Authorization": "Basic abc"}))


async def test_tampered_token_is_401(http: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    forged = jwt.encode(
        {"sub": str(user.id), "role": "ops", "type": "access", "iss": "ibackhome", "iat": 1, "exp": 2**31},
        "not-the-real-secret",
        algorithm="HS256",
    )
    await _assert_401(http.get("/anyone", headers=_bearer(forged)))


async def test_expired_token_is_401(http: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    old = datetime.now(UTC) - timedelta(minutes=get_settings().access_token_minutes + 1)
    await _assert_401(http.get("/anyone", headers=_bearer(service.create_access_token(user, now=old))))


async def test_non_access_token_is_401(http: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    now = int(datetime.now(UTC).timestamp())
    other = jwt.encode(
        {"sub": str(user.id), "type": "refresh", "iss": "ibackhome", "iat": now, "exp": now + 60},
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    await _assert_401(http.get("/anyone", headers=_bearer(other)))


async def test_refresh_token_is_not_an_access_token(http: AsyncClient) -> None:
    await _assert_401(http.get("/anyone", headers=_bearer("x" * 43)))


async def test_wrong_role_is_403(http: AsyncClient, db_session: AsyncSession) -> None:
    client_user = await make_user(db_session, role="client")
    response = await http.get("/ops-only", headers=_bearer(service.create_access_token(client_user)))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"


async def test_right_role_is_200(http: AsyncClient, db_session: AsyncSession) -> None:
    ops = await make_user(db_session, role="ops")
    response = await http.get("/ops-only", headers=_bearer(service.create_access_token(ops)))
    assert response.status_code == 200


async def test_role_change_applies_immediately(http: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, role="ops")
    token = service.create_access_token(user)  # the token still says "ops"
    user.role = "client"
    await db_session.flush()
    assert (await http.get("/ops-only", headers=_bearer(token))).status_code == 403


async def test_suspended_user_is_403(http: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session, status="suspended")
    response = await http.get("/anyone", headers=_bearer(service.create_access_token(user)))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_suspended"


def test_require_role_refuses_unknown_roles() -> None:
    with pytest.raises(ValueError):
        service.require_role("admin")
    with pytest.raises(ValueError):
        service.require_role()


async def test_me_without_token_is_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


# AI agents: a service token acts as the agent's own ops user, only on the routes it lists.


def _agent_token(user: User, *routes: str) -> str:
    return agents.create_service_token("report", routes or ["GET /ops-only"], user_id=user.id)


def test_service_token_type_matches_the_agents_module() -> None:
    assert service.SERVICE_TOKEN_TYPE == agents.SERVICE_TOKEN_TYPE


async def test_agent_reaches_a_listed_route_as_its_ops_user(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    agent_user = await make_user(db_session, role="ops")
    response = await http.get("/ops-only", headers=_bearer(_agent_token(agent_user)))
    assert response.status_code == 200
    assert response.json() == {"role": "ops"}


async def test_agent_on_an_unlisted_route_is_403(http: AsyncClient, db_session: AsyncSession) -> None:
    agent_user = await make_user(db_session, role="ops")
    response = await http.get("/anyone", headers=_bearer(_agent_token(agent_user)))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "route_not_allowed"


async def test_agent_can_never_reach_a_release_route(http: AsyncClient, db_session: AsyncSession) -> None:
    agent_user = await make_user(db_session, role="ops")
    now = datetime.now(UTC)
    forged_list = jwt.encode(  # signed with our secret, but lists a money route
        {
            "sub": str(agent_user.id),
            "type": "service",
            "agent": "rogue",
            "allowed": ["POST /milestones/{milestone_id}/release"],
            "iss": "ibackhome",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    response = await http.post("/milestones/m1/release", headers=_bearer(forged_list))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "route_not_allowed"


async def test_agent_token_signed_with_another_secret_is_401(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    agent_user = await make_user(db_session, role="ops")
    claims = jwt.decode(_agent_token(agent_user), options={"verify_signature": False})
    forged = jwt.encode(claims, "not-the-real-secret", algorithm="HS256")
    response = await http.get("/ops-only", headers=_bearer(forged))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_service_token"


async def test_agent_must_act_as_an_ops_user(http: AsyncClient, db_session: AsyncSession) -> None:
    client_user = await make_user(db_session, role="client")
    response = await http.get("/anyone", headers=_bearer(_agent_token(client_user, "GET /anyone")))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"


async def test_suspended_agent_user_is_403(http: AsyncClient, db_session: AsyncSession) -> None:
    agent_user = await make_user(db_session, role="ops", status="suspended")
    response = await http.get("/ops-only", headers=_bearer(_agent_token(agent_user)))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_suspended"


async def test_agent_in_the_real_app_is_held_to_its_list(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent_user = await make_user(db_session, role="ops")
    headers = _bearer(_agent_token(agent_user, "GET /api/v1/me"))

    me = await client.get("/api/v1/me", headers=headers)
    projects = await client.get("/api/v1/projects", headers=headers)

    assert me.status_code == 200 and me.json()["id"] == str(agent_user.id)
    assert projects.status_code == 403
    assert projects.json()["error"]["code"] == "route_not_allowed"


async def test_agent_route_with_a_path_value_matches_its_template(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    agent_user = await make_user(db_session, role="ops")
    headers = _bearer(_agent_token(agent_user, "GET /api/v1/projects/{project_id}"))

    response = await client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404  # let in; the project just doesn't exist
    assert response.json()["error"]["code"] == "project_not_found"
