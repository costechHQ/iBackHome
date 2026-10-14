"""The project state machine: every allowed move works, every other move is 409 (spec: Projects)."""

import itertools

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.projects import service
from app.features.projects.models import ProjectStatus as S
from app.features.projects.tests.factories import audit_entries, make_project, make_user
from app.features.projects.transitions import ALLOWED_TRANSITIONS, ActorRole, is_allowed

R = ActorRole

# Written out again here on purpose: changing the table must also change this test.
SPEC = {
    (S.DRAFT, S.BOQ_REVIEW): {R.CONTRACTOR},
    (S.BOQ_REVIEW, S.DRAFT): {R.CLIENT, R.CONTRACTOR, R.OPS},
    (S.BOQ_REVIEW, S.ACTIVE): {R.SYSTEM},
    (S.ACTIVE, S.PAUSED): {R.OPS},
    (S.PAUSED, S.ACTIVE): {R.OPS},
    (S.ACTIVE, S.COMPLETED): {R.SYSTEM},
}


def test_table_matches_the_spec() -> None:
    assert {pair: set(roles) for pair, roles in ALLOWED_TRANSITIONS.items()} == SPEC


@pytest.mark.parametrize(("current", "target", "role"), list(itertools.product(S, S, R)))
def test_is_allowed_only_for_listed_pairs_and_roles(current: S, target: S, role: R) -> None:
    assert is_allowed(current, target, role) is (role in SPEC.get((current, target), set()))


@pytest.mark.parametrize(("pair", "roles"), SPEC.items())
async def test_allowed_moves_work_and_are_audited(
    db_session: AsyncSession, pair: tuple[S, S], roles: set[R]
) -> None:
    current, target = pair
    role = sorted(roles)[0]
    actor = None if role == R.SYSTEM else await make_user(db_session, role.value)
    project = await make_project(db_session)
    project.status = current.value
    await db_session.flush()

    moved = await service.transition(db_session, project.id, target, role, actor.id if actor else None)
    assert moved.status == target.value

    [entry] = [
        e for e in await audit_entries(db_session, project.id) if e.action == f"project.{target.value}"
    ]
    assert entry.actor_id == (actor.id if actor else None)
    assert entry.before is not None and entry.before["status"] == current.value
    assert entry.after is not None and entry.after["status"] == target.value
    assert entry.after["actor_role"] == role.value


@pytest.mark.parametrize(
    ("current", "target"), [(c, t) for c, t in itertools.product(S, S) if (c, t) not in SPEC]
)
async def test_every_other_move_is_409(db_session: AsyncSession, current: S, target: S) -> None:
    project = await make_project(db_session)
    project.status = current.value
    await db_session.flush()
    with pytest.raises(AppError) as caught:
        await service.transition(db_session, project.id, target, R.SYSTEM)
    assert (caught.value.code, caught.value.status_code) == ("invalid_transition", 409)
    assert (await service.get_project(db_session, project.id)).status == current.value


async def test_wrong_role_for_an_allowed_move_is_403(db_session: AsyncSession) -> None:
    project = await make_project(db_session)
    with pytest.raises(AppError) as caught:
        await service.transition(db_session, project.id, S.BOQ_REVIEW, R.CLIENT)
    assert (caught.value.code, caught.value.status_code) == ("transition_not_allowed", 403)


async def test_new_projects_start_as_draft(db_session: AsyncSession) -> None:
    project = await make_project(db_session)
    assert project.status == S.DRAFT.value
