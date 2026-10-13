"""Fixtures for the login tests. Owner: Christopher.

Most tests use the shared, rolled-back `db_session` and `client` from backend/conftest.py.
The concurrency tests need several connections that really commit (one shared connection can't
race itself), so `committing_sessions` opens its own; it follows the same rules as the shared
fixtures (5 s connect timeout, fail in CI, skip locally) and deletes the rows it created.
"""

import os
import secrets
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.base.users.models import OtpCode, RefreshToken, User
from app.base.users.otp_sender import get_otp_sender
from app.core.config import get_settings
from app.core.db import CONNECT_TIMEOUT_SECONDS


def random_phone() -> str:
    """A valid Nigerian mobile number in local form, different for every test."""
    return f"0803{secrets.randbelow(10**7):07d}"


async def make_user(session: AsyncSession, *, role: str = "client", status: str = "active") -> User:
    user = User(phone="+234" + random_phone()[1:], role=role, status=status)
    session.add(user)
    await session.flush()
    return user


@dataclass
class CapturingSender:
    """Stands in for the OTP sender and keeps every code it was asked to send."""

    sent: list[tuple[str, str, str]] = field(default_factory=list)

    async def send(self, identifier: str, channel: str, code: str) -> None:
        self.sent.append((identifier, channel, code))

    @property
    def last_code(self) -> str:
        return self.sent[-1][2]


@pytest.fixture
def sender() -> Iterator[CapturingSender]:
    from app.main import app

    capturing = CapturingSender()
    app.dependency_overrides[get_otp_sender] = lambda: capturing
    yield capturing
    app.dependency_overrides.pop(get_otp_sender, None)


@dataclass
class CommittingSessions:
    factory: async_sessionmaker[AsyncSession]
    identifiers: list[str] = field(default_factory=list)  # normalised; cleaned up afterwards


@pytest.fixture
async def committing_sessions(migrated_database: None) -> AsyncIterator[CommittingSessions]:
    engine = create_async_engine(
        get_settings().database_url,
        poolclass=NullPool,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )
    try:
        async with engine.connect():
            pass
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        if os.environ.get("CI"):
            pytest.fail(f"database required in CI: {exc.__class__.__name__}")
        pytest.skip(f"database not reachable: {exc.__class__.__name__}")

    sessions = CommittingSessions(async_sessionmaker(engine, expire_on_commit=False))
    try:
        yield sessions
    finally:
        async with sessions.factory() as session:
            user_ids = select(User.id).where(
                User.phone.in_(sessions.identifiers) | User.email.in_(sessions.identifiers)
            )
            await session.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(user_ids)))
            await session.execute(delete(OtpCode).where(OtpCode.identifier.in_(sessions.identifiers)))
            await session.execute(
                delete(User).where(
                    User.phone.in_(sessions.identifiers) | User.email.in_(sessions.identifiers)
                )
            )
            await session.commit()
        await engine.dispose()
