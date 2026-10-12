"""The app boots, mounts routers under /api/v1, serves /healthz, and Celery finds every tasks.py."""

from types import ModuleType

import pytest
from fastapi import APIRouter, FastAPI
from httpx import AsyncClient

from app import main
from app.core import health
from app.core.config import get_settings
from app.core.discovery import module_names
from app.workers.celery_app import celery_app


async def test_docs_list_healthz(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    assert "/healthz" in response.json()["paths"]


async def test_api_routes_are_under_api_v1(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_every_router_py_is_mounted_under_api_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    router = APIRouter()

    @router.get("/examples")
    async def list_examples() -> list[str]:
        return []

    feature = ModuleType("app.features.example.router")
    feature.router = router  # type: ignore[attr-defined]

    empty_stub = ModuleType("app.features.stub.router")  # router.py files with no `router` are skipped
    monkeypatch.setattr(main, "import_all", lambda filename: [feature, empty_stub])

    app = FastAPI()
    app.include_router(main.build_api_router())
    assert list(app.openapi()["paths"]) == ["/api/v1/examples"]


@pytest.mark.parametrize(
    ("database", "redis", "storage", "status_code", "status"),
    [
        (True, True, True, 200, "ok"),
        (False, True, True, 503, "degraded"),
        (True, False, True, 503, "degraded"),
        (True, True, False, 503, "degraded"),
    ],
)
async def test_healthz_is_503_when_any_dependency_is_down(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    database: bool,
    redis: bool,
    storage: bool,
    status_code: int,
    status: str,
) -> None:
    async def fixed(value: bool) -> bool:
        return value

    monkeypatch.setattr(health, "check_database", lambda: fixed(database))
    monkeypatch.setattr(health, "check_redis", lambda: fixed(redis))
    monkeypatch.setattr(health, "check_storage", lambda: fixed(storage))

    response = await client.get("/healthz")

    assert response.status_code == status_code
    assert response.json() == {
        "status": status,
        "checks": {"database": database, "redis": redis, "storage": storage},
    }


async def test_storage_check_is_false_when_nothing_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "storage_endpoint", "http://127.0.0.1:1")
    assert await health.check_storage() is False


def test_celery_registers_every_tasks_py_and_runs_in_utc() -> None:
    assert celery_app.conf.include == list(module_names("tasks"))
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.accept_content == ["json"]
