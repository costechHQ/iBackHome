"""set_supervisor(): the checks live in projects, so James's route (or any caller) can't skip them."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.projects import service
from app.features.projects.models import ProjectStatus
from app.features.projects.tests.factories import (
    audit_entries,
    make_project,
    make_user,
    make_vetted_supervisor,
)


async def test_assigns_a_vetted_supervisor_and_audits_it(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    contractor = await make_user(db_session, "contractor")
    project = await make_project(db_session, contractor=contractor)
    supervisor = await make_vetted_supervisor(db_session)

    updated = await service.set_supervisor(db_session, project.id, supervisor.id, ops.id)
    assert updated.supervisor_id == supervisor.id

    [entry] = [
        e for e in await audit_entries(db_session, project.id) if e.action == "project.supervisor_assigned"
    ]
    assert entry.actor_id == ops.id
    assert entry.before is not None and entry.before["supervisor_id"] is None
    assert entry.after is not None and entry.after["supervisor_id"] == str(supervisor.id)


async def test_assigned_supervisor_becomes_a_member(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    project = await make_project(db_session)
    supervisor = await make_vetted_supervisor(db_session)
    with pytest.raises(AppError):
        await service.require_project_member(db_session, supervisor, project.id)
    await service.set_supervisor(db_session, project.id, supervisor.id, ops.id)
    assert (await service.require_project_member(db_session, supervisor, project.id)).id == project.id


async def test_replacing_the_supervisor_removes_the_old_one(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    project = await make_project(db_session)
    first = await make_vetted_supervisor(db_session)
    second = await make_vetted_supervisor(db_session)
    await service.set_supervisor(db_session, project.id, first.id, ops.id)
    await service.set_supervisor(db_session, project.id, second.id, ops.id)
    with pytest.raises(AppError) as caught:
        await service.require_project_member(db_session, first, project.id)
    assert caught.value.code == "not_project_member"


async def test_unvetted_supervisor_is_409(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    project = await make_project(db_session)
    unvetted = await make_user(db_session, "supervisor")
    with pytest.raises(AppError) as caught:
        await service.set_supervisor(db_session, project.id, unvetted.id, ops.id)
    assert (caught.value.code, caught.value.status_code) == ("supervisor_not_vetted", 409)
    assert (await service.get_project(db_session, project.id)).supervisor_id is None


async def test_supervisor_related_to_the_contractor_is_409(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    contractor = await make_user(db_session, "contractor")
    assert contractor.phone is not None
    project = await make_project(db_session, contractor=contractor)
    relative = await make_vetted_supervisor(db_session, related_to=contractor.phone)
    with pytest.raises(AppError) as caught:
        await service.set_supervisor(db_session, project.id, relative.id, ops.id)
    assert (caught.value.code, caught.value.status_code) == ("supervisor_related_to_contractor", 409)


@pytest.mark.parametrize("role", ["client", "contractor", "supplier", "ops"])
async def test_non_supervisor_is_422(db_session: AsyncSession, role: str) -> None:
    ops = await make_user(db_session, "ops")
    project = await make_project(db_session)
    other = await make_user(db_session, role)
    with pytest.raises(AppError) as caught:
        await service.set_supervisor(db_session, project.id, other.id, ops.id)
    assert (caught.value.code, caught.value.status_code) == ("not_a_supervisor", 422)


async def test_suspended_supervisor_is_409(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    project = await make_project(db_session)
    supervisor = await make_vetted_supervisor(db_session)
    supervisor.status = "suspended"
    await db_session.flush()
    with pytest.raises(AppError) as caught:
        await service.set_supervisor(db_session, project.id, supervisor.id, ops.id)
    assert caught.value.code == "supervisor_suspended"


async def test_unknown_user_or_project_is_404(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    project = await make_project(db_session)
    supervisor = await make_vetted_supervisor(db_session)
    with pytest.raises(AppError) as caught:
        await service.set_supervisor(db_session, project.id, uuid.uuid4(), ops.id)
    assert (caught.value.code, caught.value.status_code) == ("user_not_found", 404)
    with pytest.raises(AppError) as caught:
        await service.set_supervisor(db_session, uuid.uuid4(), supervisor.id, ops.id)
    assert (caught.value.code, caught.value.status_code) == ("project_not_found", 404)


async def test_completed_project_is_409(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    project = await make_project(db_session)
    project.status = ProjectStatus.COMPLETED.value
    await db_session.flush()
    supervisor = await make_vetted_supervisor(db_session)
    with pytest.raises(AppError) as caught:
        await service.set_supervisor(db_session, project.id, supervisor.id, ops.id)
    assert (caught.value.code, caught.value.status_code) == ("project_completed", 409)


async def test_same_supervisor_again_changes_nothing(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    project = await make_project(db_session)
    supervisor = await make_vetted_supervisor(db_session)
    await service.set_supervisor(db_session, project.id, supervisor.id, ops.id)
    await service.set_supervisor(db_session, project.id, supervisor.id, ops.id)
    assigned = [
        e for e in await audit_entries(db_session, project.id) if e.action == "project.supervisor_assigned"
    ]
    assert len(assigned) == 1


async def test_get_contractor_phone(db_session: AsyncSession) -> None:
    contractor = await make_user(db_session, "contractor")
    with_contractor = await make_project(db_session, contractor=contractor)
    without = await make_project(db_session)
    assert await service.get_contractor_phone(db_session, with_contractor.id) == contractor.phone
    assert await service.get_contractor_phone(db_session, without.id) is None
