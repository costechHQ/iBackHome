"""current_user and require_role, the dependencies every other module uses."""

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
