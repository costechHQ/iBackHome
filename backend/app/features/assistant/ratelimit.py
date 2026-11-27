"""Limits for the public assistant route (ADR 0006): one per IP address, and one for the whole day.

Counted in Redis (already running), so no table and no migration: the counters expire by themselves. Only a
hash of the IP address is used as a key, never the address itself, and nothing a visitor typed is stored.
If Redis is down the limits can't be counted, so the route fails open (it only costs a little CPU) and logs.
"""

import hashlib
import logging
from datetime import UTC, datetime
from typing import Protocol

from redis.asyncio import Redis

from app.core.config import get_settings

log = logging.getLogger(__name__)


class RateLimiter(Protocol):
    async def hit_ip(self, ip: str, limit: int, window_seconds: int) -> int | None:
        """Count one question from this IP. None when allowed, else the seconds until it may ask again."""
        ...

    async def hit_day(self, cap: int) -> bool:
        """Count one answer for today. False when the daily cap is already used up."""
        ...


class RedisRateLimiter:
    def __init__(self) -> None:
        self._redis: Redis | None = None

    def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(get_settings().redis_url)
        return self._redis

    async def hit_ip(self, ip: str, limit: int, window_seconds: int) -> int | None:
        key = f"assistant:ip:{hashlib.sha256(ip.encode()).hexdigest()[:24]}"
        try:
            redis = self._client()
            count = int(await redis.incr(key))
            if count == 1:
                await redis.expire(key, window_seconds)
            if count > limit:
                ttl = int(await redis.ttl(key))
                return max(1, ttl)
        except Exception:
            log.warning(
                "assistant: could not count the per-IP limit (Redis down?); letting the question through"
            )
        return None

    async def hit_day(self, cap: int) -> bool:
        key = f"assistant:day:{datetime.now(UTC):%Y%m%d}"
        try:
            redis = self._client()
            count = int(await redis.incr(key))
            if count == 1:
                await redis.expire(key, 2 * 24 * 3600)
            return count <= cap
        except Exception:
            log.warning(
                "assistant: could not count the daily cap (Redis down?); letting the question through"
            )
            return True


_limiter = RedisRateLimiter()


def get_limiter() -> RateLimiter:
    """The limiter the route uses. Tests replace it (dependency override) with an in-memory one."""
    return _limiter
