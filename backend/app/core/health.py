"""GET /healthz: checks the database, Redis and object storage. 200 when all are up, 503 otherwise."""

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine

router = APIRouter(tags=["health"])


async def check_database() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis() -> bool:
    client = Redis.from_url(get_settings().redis_url)
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


async def check_storage() -> bool:
    # Any HTTP answer below 500 (an unauthenticated request gets 403) means the S3 endpoint is up.
    # No credentials needed, so this works the same for SeaweedFS locally and R2/B2 in staging.
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(get_settings().storage_endpoint)
        return response.status_code < 500
    except httpx.HTTPError:
        return False


@router.get("/healthz")
async def healthz() -> JSONResponse:
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "storage": await check_storage(),
    }
    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )
