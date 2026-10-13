"""Idempotency-Key through a real route: optional by default, replayed, and safe under concurrency.

The route below uses `IdempotencyKeyDep` WITHOUT "= None", exactly like the module docstring
example. Each request gets its own connection that really commits (one shared, rolled-back
connection can't race itself). The fixture creates and drops its own side-effect table and
deletes the idempotency rows it used, so nothing is left behind.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.db import CONNECT_TIMEOUT_SECONDS, SessionDep, get_session
from app.core.errors import register_error_handlers
from app.core.idempotency import IdempotencyKeyDep, IdempotencyRecord, remember, replay_or_none

SCOPE = "POST /effects"
EFFECTS = "idempotency_test_effects"


class EffectIn(BaseModel):
    n: int


def build_app(factory: async_sessionmaker[AsyncSession], barrier: asyncio.Barrier | None) -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/effects")
    async def create_effect(payload: EffectIn, session: SessionDep, key: IdempotencyKeyDep) -> object:
        if (saved := await replay_or_none(session, key, SCOPE)) is not None:
            return saved
        if barrier is not None:
            await barrier.wait()  # both requests have missed the replay before either stores
        await session.execute(text(f"INSERT INTO {EFFECTS} (n) VALUES (:n)"), {"n": payload.n})  # noqa: S608
        body = {"stored": payload.n}
        await remember(session, key, SCOPE, 200, body)
        await session.commit()
        return body

    async def _own_connection() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _own_connection
    return app


class Harness:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory
        self.keys: list[str] = []

    def key(self) -> str:
        key = f"test-{uuid.uuid4()}"
        self.keys.append(key)
        return key

    def client(self, barrier: asyncio.Barrier | None = None) -> AsyncClient:
        transport = ASGITransport(app=build_app(self.factory, barrier), raise_app_exceptions=False)
        return AsyncClient(transport=transport, base_url="http://test")

    async def effects(self) -> int:
        async with self.factory() as session:
            return int(await session.scalar(text(f"SELECT count(*) FROM {EFFECTS}")) or 0)  # noqa: S608

    async def stored(self, key: str) -> int:
        async with self.factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(IdempotencyRecord).where(IdempotencyRecord.key == key)
            )
            return int(count or 0)


@pytest.fixture
async def harness(migrated_database: None) -> AsyncIterator[Harness]:
    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE TABLE IF NOT EXISTS {EFFECTS} (id serial PRIMARY KEY, n int)"))
            await conn.execute(text(f"TRUNCATE {EFFECTS}"))
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        if os.environ.get("CI"):
            pytest.fail(f"database required in CI: {exc.__class__.__name__}")
        pytest.skip(f"database not reachable: {exc.__class__.__name__}")

    h = Harness(async_sessionmaker(engine, expire_on_commit=False))
    try:
        yield h
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {EFFECTS}"))
            if h.keys:
                await conn.execute(delete(IdempotencyRecord).where(IdempotencyRecord.key.in_(h.keys)))
        await engine.dispose()


async def test_no_header_is_fine(harness: Harness) -> None:
    async with harness.client() as client:
        response = await client.post("/effects", json={"n": 1})
    assert response.status_code == 200
    assert response.json() == {"stored": 1}
    assert await harness.effects() == 1


async def test_same_key_replays_the_saved_response(harness: Harness) -> None:
    key = harness.key()
    async with harness.client() as client:
        first = await client.post("/effects", json={"n": 1}, headers={"Idempotency-Key": key})
        second = await client.post("/effects", json={"n": 1}, headers={"Idempotency-Key": key})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {"stored": 1}
    assert await harness.effects() == 1
    assert await harness.stored(key) == 1


async def test_key_clash_while_the_first_is_in_flight_is_409(harness: Harness) -> None:
    key = harness.key()
    headers = {"Idempotency-Key": key}
    async with harness.client(barrier=asyncio.Barrier(2)) as client:
        responses = await asyncio.gather(
            client.post("/effects", json={"n": 1}, headers=headers),
            client.post("/effects", json={"n": 2}, headers=headers),
        )
    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200, 409]
    clash = next(r for r in responses if r.status_code == 409)
    assert clash.json() == {
        "error": {
            "code": "idempotency_key_in_use",
            "message": "A request with this Idempotency-Key is already being processed. Retry shortly.",
        }
    }
    # The loser's side effect was rolled back with its transaction.
    assert await harness.effects() == 1
    assert await harness.stored(key) == 1


async def test_concurrent_requests_with_one_key_do_the_work_once(harness: Harness) -> None:
    key = harness.key()
    headers = {"Idempotency-Key": key}
    async with harness.client() as client:
        responses = await asyncio.gather(
            *(client.post("/effects", json={"n": 7}, headers=headers) for _ in range(5))
        )
    statuses = [r.status_code for r in responses]
    assert set(statuses) <= {200, 409}  # never a 500
    assert all(r.json() == {"stored": 7} for r in responses if r.status_code == 200)
    assert await harness.effects() == 1
    assert await harness.stored(key) == 1


# --- the real app -----------------------------------------------------------------------------


async def _openapi() -> dict[str, Any]:
    from app.main import app  # importing builds every route: a broken parameter rule fails here

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema: dict[str, Any] = response.json()
    return schema


async def test_the_whole_app_builds_its_openapi_schema() -> None:
    assert (await _openapi())["paths"]


@pytest.mark.parametrize(
    "path", ["/api/v1/auth/otp/request", "/api/v1/auth/otp/verify", "/api/v1/auth/refresh"]
)
async def test_users_routes_document_an_optional_idempotency_key(path: str) -> None:
    # Web and mobile API clients are generated from this schema.
    params = (await _openapi())["paths"][path]["post"]["parameters"]
    header = next(p for p in params if p["name"] == "Idempotency-Key")
    assert header["in"] == "header"
    assert header["required"] is False
    assert header["schema"]["anyOf"][0]["maxLength"] == 128
