"""SimulatedEscrow and get_escrow_provider(). No database needed."""

import uuid

import pytest

from app.core.errors import AppError
from app.features.escrow.providers import (
    Balance,
    EscrowProviderError,
    SimulatedEscrow,
    get_escrow_provider,
)

NGN_1M = 100_000_000  # ₦1,000,000.00 in kobo


@pytest.fixture
def escrow() -> SimulatedEscrow:
    return SimulatedEscrow()


async def test_hold_then_release(escrow: SimulatedEscrow) -> None:
    project = uuid.uuid4()
    hold = await escrow.hold(project, NGN_1M, "NGN", ref="fund-1")
    assert hold.status == "held"
    assert hold.provider_ref.startswith("simhold_")

    rel = await escrow.release(hold.provider_ref, "contractor:abc", 40_000_000, ref="rel-1")
    assert rel.status == "released"
    assert (rel.amount_minor, rel.currency, rel.hold_ref) == (40_000_000, "NGN", hold.provider_ref)

    assert await escrow.balance(project) == Balance(
        project_id=project,
        currency="NGN",
        held_minor=NGN_1M,
        released_minor=40_000_000,
        available_minor=60_000_000,
    )


async def test_provider_refs_are_deterministic() -> None:
    a, b = SimulatedEscrow(), SimulatedEscrow()
    project = uuid.uuid4()
    assert (await a.hold(project, 5, "NGN", "r")).provider_ref == (
        await b.hold(project, 5, "NGN", "r")
    ).provider_ref


async def test_same_hold_ref_twice_holds_once(escrow: SimulatedEscrow) -> None:
    project = uuid.uuid4()
    first = await escrow.hold(project, NGN_1M, "NGN", ref="fund-1")
    second = await escrow.hold(project, NGN_1M, "NGN", ref="fund-1")
    assert first == second
    assert (await escrow.balance(project)).held_minor == NGN_1M


async def test_same_release_ref_twice_releases_once(escrow: SimulatedEscrow) -> None:
    project = uuid.uuid4()
    hold = await escrow.hold(project, NGN_1M, "NGN", ref="fund-1")
    first = await escrow.release(hold.provider_ref, "contractor:abc", 30_000_000, ref="rel-1")
    second = await escrow.release(hold.provider_ref, "contractor:abc", 30_000_000, ref="rel-1")
    assert first == second
    assert (await escrow.balance(project)).released_minor == 30_000_000


async def test_reusing_a_ref_with_different_details_is_refused(escrow: SimulatedEscrow) -> None:
    project = uuid.uuid4()
    hold = await escrow.hold(project, NGN_1M, "NGN", ref="fund-1")
    with pytest.raises(AppError) as err:
        await escrow.hold(project, NGN_1M + 1, "NGN", ref="fund-1")
    assert (err.value.code, err.value.status_code) == ("escrow_ref_conflict", 409)

    await escrow.release(hold.provider_ref, "contractor:abc", 1, ref="rel-1")
    with pytest.raises(AppError) as err:
        await escrow.release(hold.provider_ref, "supplier:xyz", 1, ref="rel-1")
    assert err.value.code == "escrow_ref_conflict"


async def test_over_release_is_refused(escrow: SimulatedEscrow) -> None:
    project = uuid.uuid4()
    hold = await escrow.hold(project, NGN_1M, "NGN", ref="fund-1")
    await escrow.release(hold.provider_ref, "contractor:abc", 70_000_000, ref="rel-1")
    with pytest.raises(AppError) as err:
        await escrow.release(hold.provider_ref, "contractor:abc", 30_000_001, ref="rel-2")
    assert (err.value.code, err.value.status_code) == ("escrow_insufficient_funds", 422)
    # The refused release changed nothing; exactly the remainder still goes through.
    await escrow.release(hold.provider_ref, "contractor:abc", 30_000_000, ref="rel-2")
    assert (await escrow.balance(project)).available_minor == 0


async def test_forced_failure_raises_then_retry_succeeds(escrow: SimulatedEscrow) -> None:
    project = uuid.uuid4()
    hold = await escrow.hold(project, NGN_1M, "NGN", ref="fund-1")
    escrow.fail_next("release", times=2)

    for _ in range(2):
        with pytest.raises(EscrowProviderError) as err:
            await escrow.release(hold.provider_ref, "contractor:abc", 10, ref="rel-1")
        assert (err.value.code, err.value.status_code) == ("escrow_provider_unavailable", 502)
    assert (await escrow.balance(project)).released_minor == 0

    rel = await escrow.release(hold.provider_ref, "contractor:abc", 10, ref="rel-1")
    assert rel.status == "released"
    assert (await escrow.balance(project)).released_minor == 10


async def test_forced_hold_failure(escrow: SimulatedEscrow) -> None:
    project = uuid.uuid4()
    escrow.fail_next("hold")
    with pytest.raises(EscrowProviderError):
        await escrow.hold(project, NGN_1M, "NGN", ref="fund-1")
    assert (await escrow.balance(project)).held_minor == 0


@pytest.mark.parametrize("amount", [0, -1, 10.5, True])
async def test_invalid_amounts_refused(escrow: SimulatedEscrow, amount: int) -> None:
    with pytest.raises(AppError) as err:
        await escrow.hold(uuid.uuid4(), amount, "NGN", ref="r")
    assert err.value.code == "escrow_invalid_amount"


async def test_one_currency_per_project(escrow: SimulatedEscrow) -> None:
    project = uuid.uuid4()
    await escrow.hold(project, 100, "NGN", ref="a")
    with pytest.raises(AppError) as err:
        await escrow.hold(project, 100, "GBP", ref="b")
    assert err.value.code == "escrow_currency_mismatch"


async def test_release_from_unknown_hold(escrow: SimulatedEscrow) -> None:
    with pytest.raises(AppError) as err:
        await escrow.release("simhold_nope", "contractor:abc", 1, ref="r")
    assert (err.value.code, err.value.status_code) == ("escrow_hold_not_found", 404)


async def test_empty_project_balance(escrow: SimulatedEscrow) -> None:
    project = uuid.uuid4()
    assert await escrow.balance(project) == Balance(project, None, 0, 0, 0)


def test_factory_returns_one_simulated_instance() -> None:
    provider = get_escrow_provider()
    assert isinstance(provider, SimulatedEscrow)
    assert get_escrow_provider() is provider
