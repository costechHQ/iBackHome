"""GET /healthz: checks the database and Redis. Returns 200 when both are up, 503 otherwise."""

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


@router.get("/healthz")
async def healthz() -> JSONResponse:
    checks = {"database": await check_database(), "redis": await check_redis()}
    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )
