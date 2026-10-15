"""Milestone service against a real database: transitions, creation, and the escrow helpers."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.milestones import service
from app.features.milestones.models import Milestone
from app.features.milestones.models import MilestoneStatus as S
from app.features.milestones.schemas import MilestoneGroup
from app.features.milestones.tests.factories import make_project
from app.features.milestones.transitions import ALLOWED_TRANSITIONS, ActorRole

R = ActorRole

ALLOWED = [
    (current, target, role) for (current, target), roles in ALLOWED_TRANSITIONS.items() for role in roles
]
REFUSED_PAIRS = [(a, b) for a in S for b in S if (a, b) not in ALLOWED_TRANSITIONS]
WRONG_ROLE = [
    (current, target, role)
    for (current, target), roles in ALLOWED_TRANSITIONS.items()
    for role in R
    if role not in roles
]

STAMPS = {
    S.FUNDED: "funded_at",
    S.CLAIMED: "claimed_at",
    S.VERIFIED: "verified_at",
    S.APPROVED: "approved_at",
    S.RELEASED: "released_at",
}


async def make_milestone(session: AsyncSession, status: S = S.PENDING) -> Milestone:
    project = await make_project(session)
    milestone = Milestone(
        project_id=project.id,
        sequence=1,
        name="Foundation",
        amount_minor=150_000_000,
        currency="NGN",
        status=status,
    )
    session.add(milestone)
    await session.flush()
    return milestone


# --- transition() -------------------------------------------------------------------------


@pytest.mark.parametrize(("current", "target", "role"), ALLOWED)
async def test_every_allowed_move_succeeds(db_session: AsyncSession, current: S, target: S, role: R) -> None:
    milestone = await make_milestone(db_session, current)
    result = await service.transition(db_session, milestone.id, target, role, uuid.uuid4())
    assert result.status == target
    if target in STAMPS:
        assert getattr(result, STAMPS[target]) is not None


@pytest.mark.parametrize(("current", "target"), REFUSED_PAIRS)
async def test_every_other_pair_is_refused_with_409(db_session: AsyncSession, current: S, target: S) -> None:
    milestone = await make_milestone(db_session, current)
    for role in R:
        with pytest.raises(AppError) as error:
            await service.transition(db_session, milestone.id, target, role)
        assert error.value.status_code == 409
        assert error.value.code == "invalid_transition"
    assert (await service.get_milestone(db_session, milestone.id)).status == current


@pytest.mark.parametrize(("current", "target", "role"), WRONG_ROLE)
async def test_allowed_move_by_wrong_role_is_refused_with_403(
    db_session: AsyncSession, current: S, target: S, role: R
) -> None:
    milestone = await make_milestone(db_session, current)
    with pytest.raises(AppError) as error:
        await service.transition(db_session, milestone.id, target, role)
    assert error.value.status_code == 403
    assert error.value.code == "transition_not_allowed"
    assert (await service.get_milestone(db_session, milestone.id)).status == current


async def test_unknown_milestone_is_404(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await service.transition(db_session, uuid.uuid4(), S.FUNDED, R.SYSTEM)
    assert error.value.status_code == 404


async def test_rejected_claim_clears_the_claim(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.FUNDED)
    await service.transition(db_session, milestone.id, S.CLAIMED, R.CONTRACTOR)
    result = await service.transition(db_session, milestone.id, S.FUNDED, R.SUPERVISOR)
    assert result.status == S.FUNDED
    assert result.claimed_at is None


# --- create_for_project() (for Christopher) -------------------------------------------------


async def test_create_for_project_makes_pending_milestones_in_order(db_session: AsyncSession) -> None:
    project_id = (await make_project(db_session)).id
    groups = [
        MilestoneGroup(name="Foundation", amount_minor=150_000_000),
        MilestoneGroup(name="Blockwork to lintel", amount_minor=220_000_000),
        MilestoneGroup(name="Roofing", amount_minor=180_000_000),
    ]
    created = await service.create_for_project(db_session, project_id, groups, "NGN")

    assert [m.sequence for m in created] == [1, 2, 3]
    assert [m.name for m in created] == ["Foundation", "Blockwork to lintel", "Roofing"]
    assert all(m.status == S.PENDING and m.currency == "NGN" for m in created)
    listed = await service.list_for_project(db_session, project_id)
    assert [m.id for m in listed] == [m.id for m in created]


async def test_create_for_project_twice_is_refused(db_session: AsyncSession) -> None:
    project_id = (await make_project(db_session)).id
    groups = [MilestoneGroup(name="Foundation", amount_minor=1_000)]
    await service.create_for_project(db_session, project_id, groups, "NGN")
    with pytest.raises(AppError) as error:
        await service.create_for_project(db_session, project_id, groups, "NGN")
    assert error.value.status_code == 409
    assert error.value.code == "milestones_already_exist"


@pytest.mark.parametrize(
    ("groups", "currency", "code"),
    [
        ([], "NGN", "no_milestones"),
        ([MilestoneGroup(name="Foundation", amount_minor=1)], "naira", "invalid_currency"),
        ([MilestoneGroup(name="Foundation", amount_minor=1)], "ngn", "invalid_currency"),
        (
            [MilestoneGroup(name=f"Stage {i}", amount_minor=1) for i in range(21)],
            "NGN",
            "too_many_milestones",
        ),
    ],
)
async def test_create_for_project_validates_input(
    db_session: AsyncSession, groups: list[MilestoneGroup], currency: str, code: str
) -> None:
    with pytest.raises(AppError) as error:
        await service.create_for_project(db_session, (await make_project(db_session)).id, groups, currency)
    assert error.value.code == code


def test_milestone_amount_must_be_positive() -> None:
    with pytest.raises(ValueError, match="greater than 0"):
        MilestoneGroup(name="Foundation", amount_minor=0)


# --- helpers for Gabriel (escrow) -------------------------------------------------------------


async def test_full_happy_path_with_helpers(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.PENDING)
    await service.mark_funded(db_session, milestone.id)
    await service.transition(db_session, milestone.id, S.CLAIMED, R.CONTRACTOR)
    await service.transition(db_session, milestone.id, S.VERIFIED, R.SUPERVISOR)
    await service.transition(db_session, milestone.id, S.APPROVED, R.CLIENT)
    result = await service.mark_released(db_session, milestone.id)
    assert result.status == S.RELEASED
    assert result.released_at is not None


async def test_dispute_resolved_as_rework_goes_back_to_funded(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.VERIFIED)
    milestone.claimed_at = milestone.created_at
    await service.mark_disputed(db_session, milestone.id, uuid.uuid4())
    result = await service.mark_resolved(db_session, milestone.id, "rework", uuid.uuid4())
    assert result.status == S.FUNDED
    assert result.claimed_at is None
    assert result.verified_at is None


async def test_dispute_resolved_as_release(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.VERIFIED)
    await service.mark_disputed(db_session, milestone.id, uuid.uuid4())
    result = await service.mark_resolved(db_session, milestone.id, "release", uuid.uuid4())
    assert result.status == S.RELEASED


async def test_mark_released_refuses_a_milestone_that_is_not_approved(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.VERIFIED)
    with pytest.raises(AppError) as error:
        await service.mark_released(db_session, milestone.id)
    assert error.value.status_code == 409


async def test_mark_resolved_rejects_unknown_outcome(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.DISPUTED)
    with pytest.raises(AppError) as error:
        await service.mark_resolved(db_session, milestone.id, "refund", uuid.uuid4())  # type: ignore[arg-type]
    assert error.value.code == "invalid_outcome"
