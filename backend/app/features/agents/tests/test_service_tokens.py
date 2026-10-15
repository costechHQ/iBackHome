"""Agent service tokens (service.py). No database needed."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.errors import AppError, register_error_handlers
from app.features.agents import service

AGENT_USER = uuid.uuid4()
READ_PROJECT = "GET /api/v1/projects/{project_id}"


def token(*routes: str, **kwargs: object) -> str:
    return service.create_service_token("report", routes or [READ_PROJECT], user_id=AGENT_USER, **kwargs)  # type: ignore[arg-type]


def test_token_round_trip_keeps_agent_user_and_routes() -> None:
    claims = service.decode_service_token(token(READ_PROJECT, "get /api/v1/projects/{project_id}/boq/"))

    assert (claims["sub"], claims["agent"], claims["type"]) == (str(AGENT_USER), "report", "service")
    assert claims["allowed"] == ["GET /api/v1/projects/{project_id}", "GET /api/v1/projects/{project_id}/boq"]
    assert claims["exp"] - claims["iat"] == service.SERVICE_TOKEN_MINUTES * 60


@pytest.mark.parametrize(
    "route",
    [
        "POST /api/v1/milestones/{milestone_id}/approve",
        "POST /api/v1/milestones/{milestone_id}/release",
        "POST /api/v1/escrow/releases",
        "POST /api/v1/disputes/{dispute_id}/resolve",
        "POST /api/v1/projects/{project_id}/funding",
        "POST /api/v1/payouts",
        "POST /api/v1/orders/{order_id}/pay",
        "POST /api/v1/webhooks/stripe",
        "POST /api/v1/auth/otp/request",
        "POST /api/v1/projects/{project_id}/boq/approve",
    ],
)
def test_a_money_or_decision_route_can_never_be_put_on_a_token(route: str) -> None:
    with pytest.raises(ValueError, match="may never call"):
        token(route)


@pytest.mark.parametrize("route", ["/api/v1/projects", "FETCH /api/v1/projects", "GET api/v1/projects"])
def test_malformed_routes_are_refused(route: str) -> None:
    with pytest.raises(ValueError, match="not a route"):
        token(route)


def test_listed_route_is_allowed() -> None:
    service.check_route(service.decode_service_token(token()), "GET", "/api/v1/projects/{project_id}")


def test_unlisted_route_is_403() -> None:
    claims = service.decode_service_token(token())

    with pytest.raises(AppError) as error:
        service.check_route(claims, "PUT", "/api/v1/projects/{project_id}/site")

    assert (error.value.code, error.value.status_code) == ("route_not_allowed", 403)


def test_forbidden_route_is_403_even_if_a_token_lists_it() -> None:
    # A token forged with the right secret but a money route on its list is still refused.
    now = datetime.now(UTC)
    claims = {
        "type": "service",
        "agent": "rogue",
        "allowed": ["POST /api/v1/milestones/{milestone_id}/release"],
    }
    forged = jwt.encode(
        claims | {"sub": str(AGENT_USER), "iss": "ibackhome", "iat": now, "exp": now + timedelta(minutes=5)},
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(AppError) as error:
        service.check_route(
            service.decode_service_token(forged), "POST", "/api/v1/milestones/{milestone_id}/release"
        )

    assert error.value.code == "route_not_allowed"


def test_expired_token_is_401() -> None:
    old = token(now=datetime.now(UTC) - timedelta(hours=1))

    with pytest.raises(AppError) as error:
        service.decode_service_token(old)

    assert (error.value.code, error.value.status_code) == ("invalid_service_token", 401)


def test_login_token_is_not_a_service_token() -> None:
    now = datetime.now(UTC)
    access = jwt.encode(
        {
            "sub": str(AGENT_USER),
            "type": "access",
            "iss": "ibackhome",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(AppError) as error:
        service.decode_service_token(access)

    assert error.value.status_code == 401


def test_token_signed_with_another_secret_is_401() -> None:
    claims = jwt.decode(token(), options={"verify_signature": False})
    tampered = jwt.encode(
        claims | {"allowed": ["GET /api/v1/ops/audit"]}, "not-our-secret", algorithm="HS256"
    )

    with pytest.raises(AppError):
        service.decode_service_token(tampered)


# End to end in a real request: the hook proposed for users.current_user, in a stand-in app.

bearer = HTTPBearer(auto_error=False)


async def agent_guard(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> None:
    if credentials is None:
        raise AppError("unauthorized", "Sign in first.", 401)
    claims = service.decode_service_token(credentials.credentials)
    service.check_route(claims, request.method, request.scope["route"].path)


@pytest.fixture
async def http() -> AsyncIterator[AsyncClient]:
    app = FastAPI(dependencies=[Depends(agent_guard)])
    register_error_handlers(app)

    @app.get("/api/v1/projects/{project_id}")
    async def get_project(project_id: uuid.UUID) -> dict[str, str]:
        return {"id": str(project_id)}

    @app.post("/api/v1/milestones/{milestone_id}/release")
    async def release(milestone_id: uuid.UUID) -> dict[str, str]:
        return {"released": str(milestone_id)}  # pragma: no cover - must never be reached

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_agent_token_reaches_its_allowed_route(http: AsyncClient) -> None:
    response = await http.get(
        f"/api/v1/projects/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token()}"}
    )

    assert response.status_code == 200


async def test_agent_token_gets_403_on_a_release_route(http: AsyncClient) -> None:
    response = await http.post(
        f"/api/v1/milestones/{uuid.uuid4()}/release", headers={"Authorization": f"Bearer {token()}"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "route_not_allowed"
