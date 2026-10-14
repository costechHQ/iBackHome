"""Supervisor rotation (rotation.py). Needs Postgres (backend/conftest.py)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.projects import service as projects
from app.features.projects.models import Project
from app.features.supervision import rotation
from app.features.supervision.schemas import DeclaredRelation
from app.features.supervision.tests.factories import CONTRACTOR_PHONE, make_vetted

A, B = uuid.uuid4(), uuid.uuid4()


class Offered:
    """Stands in for the random pick: remembers who was offered and takes the first."""

    def __init__(self) -> None:
        self.candidates: list[uuid.UUID] = []

    def __call__(self, candidates: list[uuid.UUID]) -> uuid.UUID:
        self.candidates = list(candidates)
        return candidates[0]


@pytest.mark.parametrize(
    ("current", "verifiers", "due"),
    [
        (A, [], False),
        (A, [A], False),  # only one milestone so far
        (A, [A, A], True),  # two in a row
        (A, [B, A, A], True),
        (A, [A, B], False),  # not consecutive
        (A, [A, A, B], False),  # B did the last one
        (None, [A, A], False),  # nobody assigned
    ],
)
def test_rotation_is_due_after_two_consecutive_milestones(
    current: uuid.UUID | None, verifiers: list[uuid.UUID], due: bool
) -> None:
    assert rotation.rotation_due(current, verifiers) is due


async def assigned(session: AsyncSession, project: Project, ops: User) -> User:
    current = await make_vetted(session, ops)
    await projects.set_supervisor(session, project.id, current.id, ops.id)
    return current


async def test_replacement_is_vetted_and_not_the_current_supervisor(
    db_session: AsyncSession, project: Project, ops: User, applicant: User
) -> None:
    current = await assigned(db_session, project, ops)
    other = await make_vetted(db_session, ops)
    offered = Offered()

    await rotation.pick_replacement(db_session, project.id, choose=offered)

    assert other.id in offered.candidates
    assert current.id not in offered.candidates
    assert applicant.id not in offered.candidates  # applied but not vetted


async def test_replacement_is_never_related_to_the_contractor(
    db_session: AsyncSession, project: Project, ops: User
) -> None:
    await assigned(db_session, project, ops)
    cousin = await make_vetted(
        db_session, ops, DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="cousin")
    )
    offered = Offered()

    await rotation.pick_replacement(db_session, project.id, choose=offered)

    assert cousin.id not in offered.candidates


async def test_suspended_supervisor_is_not_offered(
    db_session: AsyncSession, project: Project, ops: User
) -> None:
    await assigned(db_session, project, ops)
    suspended = await make_vetted(db_session, ops)
    suspended.status = "suspended"
    await db_session.flush()
    offered = Offered()

    await rotation.pick_replacement(db_session, project.id, choose=offered)

    assert suspended.id not in offered.candidates


async def test_next_supervisor_is_none_until_rotation_is_due(
    db_session: AsyncSession, project: Project, ops: User
) -> None:
    current = await assigned(db_session, project, ops)
    await make_vetted(db_session, ops)

    assert await rotation.next_supervisor(db_session, project.id, [current.id]) is None


async def test_next_supervisor_can_be_assigned_when_rotation_is_due(
    db_session: AsyncSession, project: Project, ops: User
) -> None:
    current = await assigned(db_session, project, ops)
    await make_vetted(db_session, ops)

    replacement = await rotation.next_supervisor(db_session, project.id, [current.id, current.id])

    assert replacement is not None and replacement != current.id
    updated = await projects.set_supervisor(db_session, project.id, replacement, ops.id)
    assert updated.supervisor_id == replacement


async def test_the_pick_is_random_by_default(db_session: AsyncSession, project: Project, ops: User) -> None:
    await assigned(db_session, project, ops)
    others = {(await make_vetted(db_session, ops)).id for _ in range(4)}

    picks = {await rotation.pick_replacement(db_session, project.id) for _ in range(40)}

    assert len(picks & others) > 1  # 40 draws from 4+ people: one person every time is ~1 in 10^23


async def test_non_supervisor_with_old_vetting_is_not_offered(
    db_session: AsyncSession, project: Project, ops: User
) -> None:
    await assigned(db_session, project, ops)
    changed_role = await make_vetted(db_session, ops)
    changed_role.role = "client"
    await db_session.flush()
    offered = Offered()

    await rotation.pick_replacement(db_session, project.id, choose=offered)

    assert changed_role.id not in offered.candidates
