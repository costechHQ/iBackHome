"""The per-IP OTP limit uses the real caller and can't be dodged by faking X-Forwarded-For.

`uvicorn --proxy-headers` wraps the app in uvicorn's ProxyHeadersMiddleware, which trusts
X-Forwarded-For only from FORWARDED_ALLOW_IPS. These tests wrap app.main in that same middleware.
"""

from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.base.users.models import OtpCode
from app.base.users.tests.conftest import CapturingSender, random_phone
from app.core.config import get_settings

REQUEST = "/api/v1/auth/otp/request"


def _behind_proxy_middleware(peer: str) -> AsyncClient:
    from app.main import app

    # uvicorn's strict ASGI types and Starlette/httpx's looser ones describe the same interface.
    wrapped: Any = ProxyHeadersMiddleware(cast(Any, app), trusted_hosts="127.0.0.1")  # the local default
    transport = ASGITransport(app=wrapped, client=(peer, 50000))
    return AsyncClient(transport=transport, base_url="http://test")


async def _recorded_ips(session: AsyncSession) -> list[str]:
    return list((await session.scalars(select(OtpCode.requested_ip))).all())


async def test_faked_forwarded_for_from_an_untrusted_peer_does_not_bypass_the_ip_limit(
    client: AsyncClient,  # routes the app to the test's rolled-back db_session
    sender: CapturingSender,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "otp_limit_per_ip", 2)
    async with _behind_proxy_middleware("203.0.113.9") as attacker:
        statuses = [
            (
                await attacker.post(
                    REQUEST,
                    json={"identifier": random_phone()},
                    headers={"X-Forwarded-For": f"198.51.100.{n}"},  # a new fake IP every time
                )
            ).status_code
            for n in range(3)
        ]
    assert statuses == [202, 202, 429]
    assert await _recorded_ips(db_session) == ["203.0.113.9", "203.0.113.9"]


async def test_a_trusted_proxy_passes_the_real_caller_ip(
    client: AsyncClient, sender: CapturingSender, db_session: AsyncSession
) -> None:
    async with _behind_proxy_middleware("127.0.0.1") as proxy:
        response = await proxy.post(
            REQUEST, json={"identifier": random_phone()}, headers={"X-Forwarded-For": "198.51.100.20"}
        )
    assert response.status_code == 202
    assert await _recorded_ips(db_session) == ["198.51.100.20"]
