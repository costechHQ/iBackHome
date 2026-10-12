"""Every error leaves the API in one shape: {"error": {"code": ..., "message": ...}}."""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.errors import AppError, register_error_handlers


class Payload(BaseModel):
    amount_minor: int


def build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/app-error")
    async def app_error() -> None:
        raise AppError("milestone_not_verified", "This milestone has not been verified yet.", 409)

    @app.get("/rate-limited")
    async def rate_limited() -> None:
        raise HTTPException(429, detail="Too many codes requested.", headers={"Retry-After": "60"})

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("database password is hunter2")

    @app.post("/validate")
    async def validate(payload: Payload) -> Payload:
        return payload

    return app


@pytest.fixture
async def http() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=build_app(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_app_error_uses_its_code_and_status(http: AsyncClient) -> None:
    response = await http.get("/app-error")
    assert response.status_code == 409
    assert response.json() == {
        "error": {"code": "milestone_not_verified", "message": "This milestone has not been verified yet."}
    }


async def test_unknown_route_is_not_found(http: AsyncClient) -> None:
    response = await http.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_wrong_method_is_method_not_allowed(http: AsyncClient) -> None:
    response = await http.post("/app-error")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


async def test_http_exception_keeps_its_headers(http: AsyncClient) -> None:
    response = await http.get("/rate-limited")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert response.json() == {"error": {"code": "rate_limited", "message": "Too many codes requested."}}


async def test_validation_error_names_the_field(http: AsyncClient) -> None:
    response = await http.post("/validate", json={"amount_minor": "lots"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "amount_minor" in body["error"]["message"]


async def test_unhandled_error_is_500_without_leaking_details(http: AsyncClient) -> None:
    response = await http.get("/crash")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "hunter2" not in response.text
