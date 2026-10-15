"""Fixtures for supervision tests. `db_session` and `client` come from backend/conftest.py."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.projects.models import Project
from app.features.supervision import service
from app.features.supervision.tests.factories import (
    CONTRACTOR_PHONE,
    application,
    make_project,
    make_user,
    make_vetted,
)


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
    return await make_vetted(db_session, ops)


@pytest.fixture
async def project(db_session: AsyncSession) -> Project:
    """A draft project whose contractor has the phone CONTRACTOR_PHONE."""
    return await make_project(db_session, contractor_phone=CONTRACTOR_PHONE)
