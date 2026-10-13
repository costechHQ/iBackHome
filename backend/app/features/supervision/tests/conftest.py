"""Fixtures for supervision tests. `db_session` and `client` come from backend/conftest.py."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.supervision import service
from app.features.supervision.tests.factories import application, approval, make_user


@pytest.fixture
async def ops(db_session: AsyncSession) -> User:
    return await make_user(db_session, "ops")


@pytest.fixture
async def applicant(db_session: AsyncSession) -> User:
    """A supervisor who has applied and is waiting for ops."""
    user = await make_user(db_session, "supervisor")
    await service.submit_application(db_session, user.id, application())
    return user


@pytest.fixture
async def vetted(db_session: AsyncSession, ops: User) -> User:
    """A supervisor ops has approved."""
    user = await make_user(db_session, "supervisor")
    await service.submit_application(db_session, user.id, application())
    await service.vet(db_session, user.id, approval(), ops.id)
    return user
