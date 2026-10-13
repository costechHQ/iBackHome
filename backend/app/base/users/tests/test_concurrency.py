"""Races: each test runs requests at the same time on separate, committing connections."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service
from app.base.users.models import OtpCode, RefreshToken, User
from app.base.users.tests.conftest import CapturingSender, CommittingSessions, random_phone
from app.core.config import get_settings
from app.core.errors import AppError

IP = "203.0.113.50"


def _e164(local: str) -> str:
    return "+234" + local[1:]


async def _in_own_session(
    sessions: CommittingSessions, work: Callable[[AsyncSession], Awaitable[Any]]
) -> Any:
    async with sessions.factory() as session:
        try:
            return await work(session)
        except (AppError, HTTPException) as exc:
            await session.rollback()
            return exc


async def _signed_in(sessions: CommittingSessions, sender: CapturingSender) -> tuple[str, str]:
    phone = random_phone()
    sessions.identifiers.append(_e164(phone))

    async def go(session: AsyncSession) -> Any:
        await service.request_otp(session, phone, IP, sender)
        await session.commit()
        return await service.verify_otp(session, phone, sender.last_code)

    tokens = await _in_own_session(sessions, go)
    return phone, tokens.refresh_token


async def test_a_refresh_token_never_rotates_twice(committing_sessions: CommittingSessions) -> None:
    _, refresh_token = await _signed_in(committing_sessions, CapturingSender())

    results = await asyncio.gather(
        *(
            _in_own_session(committing_sessions, lambda s: service.rotate_refresh_token(s, refresh_token))
            for _ in range(2)
        )
    )
    winners = [r for r in results if not isinstance(r, Exception)]
    losers = [r for r in results if isinstance(r, AppError)]
    assert len(winners) == 1
    assert len(losers) == 1 and losers[0].code == "refresh_token_reused"

    async with committing_sessions.factory() as session:
        old = await session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == service._token_hash(refresh_token))
        )
        assert old is not None and old.used_at is not None and old.replaced_by_id is not None
        replacements = await session.scalar(
            select(func.count()).select_from(RefreshToken).where(RefreshToken.id == old.replaced_by_id)
        )
        assert replacements == 1


async def test_a_code_signs_in_only_once_when_sent_twice_at_once(
    committing_sessions: CommittingSessions,
) -> None:
    sender = CapturingSender()
    phone = random_phone()
    committing_sessions.identifiers.append(_e164(phone))

    async def request(session: AsyncSession) -> None:
        await service.request_otp(session, phone, IP, sender)
        await session.commit()

    await _in_own_session(committing_sessions, request)
    code = sender.last_code

    results = await asyncio.gather(
        *(
            _in_own_session(committing_sessions, lambda s: service.verify_otp(s, phone, code))
            for _ in range(2)
        )
    )
    assert sum(1 for r in results if not isinstance(r, Exception)) == 1
    assert [r.code for r in results if isinstance(r, AppError)] == ["invalid_code"]

    async with committing_sessions.factory() as session:
        users = await session.scalar(select(func.count()).select_from(User).where(User.phone == _e164(phone)))
        assert users == 1


async def test_concurrent_wrong_codes_stop_at_the_attempt_limit(
    committing_sessions: CommittingSessions,
) -> None:
    sender = CapturingSender()
    phone = random_phone()
    committing_sessions.identifiers.append(_e164(phone))

    async def request(session: AsyncSession) -> None:
        await service.request_otp(session, phone, IP, sender)
        await session.commit()

    await _in_own_session(committing_sessions, request)
    code = sender.last_code
    wrong = f"{(int(code) + 1) % 10**6:06d}"
    max_attempts = get_settings().otp_max_attempts

    results = await asyncio.gather(
        *(
            _in_own_session(committing_sessions, lambda s: service.verify_otp(s, phone, wrong))
            for _ in range(max_attempts + 3)
        )
    )
    codes = sorted(r.code for r in results if isinstance(r, AppError))
    assert codes.count("invalid_code") == max_attempts
    assert codes.count("too_many_attempts") == 3

    async with committing_sessions.factory() as session:
        row = await session.scalar(select(OtpCode).where(OtpCode.identifier == _e164(phone)))
        assert row is not None and row.attempts == max_attempts

    late = await _in_own_session(committing_sessions, lambda s: service.verify_otp(s, phone, code))
    assert isinstance(late, AppError) and late.code == "too_many_attempts"


async def test_concurrent_requests_cannot_beat_the_rate_limit(
    committing_sessions: CommittingSessions,
) -> None:
    sender = CapturingSender()
    phone = random_phone()
    committing_sessions.identifiers.append(_e164(phone))
    limit = get_settings().otp_limit_per_identifier

    async def request(session: AsyncSession) -> int:
        expires_in = await service.request_otp(session, phone, IP, sender)
        await session.commit()
        return expires_in

    results = await asyncio.gather(*(_in_own_session(committing_sessions, request) for _ in range(limit + 2)))
    assert sum(1 for r in results if isinstance(r, int)) == limit
    assert sum(1 for r in results if isinstance(r, HTTPException) and r.status_code == 429) == 2
    assert len(sender.sent) == limit
