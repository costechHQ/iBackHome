"""The state machine table itself: every (from, to, role) combination. No database needed."""

import itertools

import pytest

from app.features.milestones.models import MilestoneStatus as S
from app.features.milestones.transitions import ALLOWED_TRANSITIONS, ActorRole, is_allowed

R = ActorRole

# Copied from the spec's milestone table on purpose: changing the state machine
# must mean changing this test too.
SPEC = {
    (S.PENDING, S.FUNDED): {R.SYSTEM},
    (S.FUNDED, S.CLAIMED): {R.CONTRACTOR},
    (S.CLAIMED, S.VERIFIED): {R.SUPERVISOR},
    (S.CLAIMED, S.FUNDED): {R.SUPERVISOR},
    (S.VERIFIED, S.APPROVED): {R.CLIENT},
    (S.VERIFIED, S.DISPUTED): {R.CLIENT},
    (S.APPROVED, S.RELEASED): {R.SYSTEM},
    (S.DISPUTED, S.RELEASED): {R.OPS},
    (S.DISPUTED, S.FUNDED): {R.OPS},
}

ALL_COMBINATIONS = list(itertools.product(S, S, R))


def test_table_matches_spec() -> None:
    assert {pair: set(roles) for pair, roles in ALLOWED_TRANSITIONS.items()} == SPEC


@pytest.mark.parametrize(("current", "target", "role"), ALL_COMBINATIONS)
def test_every_combination(current: S, target: S, role: R) -> None:
    expected = role in SPEC.get((current, target), set())
    assert is_allowed(current, target, role) is expected


def test_released_is_final() -> None:
    assert not any(current == S.RELEASED for current, _ in ALLOWED_TRANSITIONS)


def test_no_state_moves_to_itself() -> None:
    assert not any(current == target for current, target in ALLOWED_TRANSITIONS)


def test_every_state_except_pending_can_be_reached() -> None:
    reachable = {target for _, target in ALLOWED_TRANSITIONS}
    assert reachable == set(S) - {S.PENDING}
