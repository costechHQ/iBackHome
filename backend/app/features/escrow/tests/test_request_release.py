"""Releasing an approved milestone: request_release -> escrow.submit_release -> confirmed ->
contractor payout. Day 4 "done when": an approved milestone ends released with the contractor
paid in the ledger; every transaction balances; retries and duplicate events are safe."""

import inspect
import uuid
from collections.abc import Iterator
from typing import get_type_hints

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import accounts, balance
from app.base.payments import service as payments_service
from app.base.payments import tasks as payments_tasks
from app.base.payments.models import Payout
from app.base.payments.paystack import TransferResult
from app.base.payments.tests.webhook_helpers import webhook_secrets
from app.base.users.models import User
from app.core.errors import AppError
from app.features.escrow import service as escrow
from app.features.escrow import tasks as escrow_tasks
from app.features.escrow.models import EscrowAccount, EscrowRelease
from app.features.escrow.providers import ReleaseResult
from app.features.escrow.service import ReleaseRequest, request_release
from app.features.escrow.tests.factories import (
    BLOCKWORK_NGN,
    FOUNDATION_NGN,
    Funded,
    make_active_project,
    simulated_escrow,
)
from app.features.escrow.tests.release_helpers import (
    FakePaystack,
    Queued,
    add_recipient,
    all_entries,
    approve_milestone,
    entries_of_release,
    hold_milestone,
    release_event,
    send_escrow,
    send_paystack,
    session_factory,
    transfer_event,
    unbalanced,
)
from app.features.milestones import service as milestones
from app.features.milestones.models import Milestone, MilestoneStatus
from app.features.projects.tests.factories import audit_entries


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with webhook_secrets(monkeypatch):
        yield


@pytest.fixture(autouse=True)
def _fresh_escrow() -> Iterator[None]:
    simulated_escrow().reset()
    yield
    simulated_escrow().reset()


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> Queued:
    spy = Queued()
    monkeypatch.setattr(escrow, "enqueue_submit_release", spy.releases.append)
    monkeypatch.setattr(payments_service, "enqueue_send_transfer", spy.payouts.append)
    return spy


@pytest.fixture
def paystack(monkeypatch: pytest.MonkeyPatch) -> FakePaystack:
    fake = FakePaystack()
    monkeypatch.setattr(payments_service, "get_paystack_client", lambda: fake)
    return fake


async def approved(db_session: AsyncSession, *, recipient: bool = True) -> Funded:
    """An active project whose foundation milestone is held in escrow and approved by the client."""
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)
    await approve_milestone(db_session, funded, funded.foundation)
    if recipient:
        await add_recipient(db_session, user_id=funded.contractor.id)
    return funded


async def milestone_status(db_session: AsyncSession, milestone: Milestone) -> MilestoneStatus:
    await db_session.refresh(milestone)
    return milestone.status


async def payout_of(db_session: AsyncSession, release_id: uuid.UUID) -> Payout | None:
    return await db_session.scalar(
        select(Payout).where(Payout.reference == escrow.payout_reference(release_id))
    )


async def actions(db_session: AsyncSession, object_id: uuid.UUID) -> list[str]:
    return [e.action for e in await audit_entries(db_session, object_id)]


# --- the agreed signature (Lilian codes against it) ---------------------------------------------


def test_signature_is_the_agreed_one() -> None:
    assert inspect.iscoroutinefunction(request_release)
    assert list(inspect.signature(request_release).parameters) == ["session", "milestone_id", "actor"]
    hints = get_type_hints(request_release)
    assert hints["session"] is AsyncSession
    assert hints["milestone_id"] is uuid.UUID
    assert hints["actor"] is User
    assert hints["return"] is ReleaseRequest


# --- the whole path ---------------------------------------------------------------------------


async def test_approved_milestone_ends_released_with_the_contractor_paid(
    client: AsyncClient, db_session: AsyncSession, queued: Queued, paystack: FakePaystack
) -> None:
    funded = await approved(db_session)
    factory = session_factory(db_session)

    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    assert result.status == "requested"
    assert result.milestone_id == funded.foundation.id
    assert queued.releases == []  # nothing is queued before the caller commits
    await db_session.commit()
    assert queued.releases == [result.release_id]

    assert await escrow_tasks.run_submit_release(factory, result.release_id, retries=0) == "done"
    release = await escrow.get_release(db_session, result.release_id)
    assert (release.status, release.attempts) == ("released", 1)
    assert release.provider_ref and release.provider_ref.startswith("simrel_")
    assert await milestone_status(db_session, funded.foundation) == MilestoneStatus.RELEASED

    # Released: escrow -> contractor_payable, and the payout is saved before Paystack is called.
    project = funded.project.id
    assert await balance(db_session, accounts.escrow(project, "NGN")) == 0
    assert await balance(db_session, accounts.contractor_payable("NGN")) == FOUNDATION_NGN
    account = await db_session.scalar(select(EscrowAccount).where(EscrowAccount.project_id == project))
    assert account is not None and account.balance_minor == 0  # the cache matches the ledger
    payout = await payout_of(db_session, release.id)
    assert payout is not None
    assert (payout.status, payout.provider_transfer_code, payout.amount_minor) == (
        "pending",
        None,
        FOUNDATION_NGN,
    )
    assert queued.payouts == [payout.id]

    assert await payments_tasks.run_send_transfer(factory, payout.id, retries=0) == "done"
    await db_session.refresh(payout)
    assert payout.provider_transfer_code and paystack.initiated == [payout.reference]

    response = await send_paystack(client, transfer_event("transfer.success", payout))
    assert response.status_code == 200, response.text

    await db_session.refresh(payout)
    assert payout.status == "success"
    assert await balance(db_session, accounts.contractor_payable("NGN")) == 0
    assert await balance(db_session, accounts.escrow_payouts("NGN")) == FOUNDATION_NGN
    # Two transactions on the release: escrow -> payable on release, payable -> paid out on payout.
    by_transaction: dict[uuid.UUID, set[tuple[str, str, int]]] = {}
    for e in await entries_of_release(db_session, release.id):
        by_transaction.setdefault(e.transaction_id, set()).add((e.account, e.direction, e.amount_minor))
    assert {frozenset(lines) for lines in by_transaction.values()} == {
        frozenset(
            {
                (accounts.contractor_payable("NGN"), "debit", FOUNDATION_NGN),
                (accounts.escrow(project, "NGN"), "credit", FOUNDATION_NGN),
            }
        ),
        frozenset(
            {
                (accounts.escrow_payouts("NGN"), "debit", FOUNDATION_NGN),
                (accounts.contractor_payable("NGN"), "credit", FOUNDATION_NGN),
            }
        ),
    }
    assert unbalanced(await all_entries(db_session)) == {}
    assert await actions(db_session, release.id) == [
        "escrow.release_requested",
        "escrow.released",
        "escrow.payout_confirmed",
    ]


async def test_requesting_twice_returns_the_same_release(db_session: AsyncSession, queued: Queued) -> None:
    funded = await approved(db_session)
    first = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    second = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    assert first == second
    count = await db_session.scalar(
        select(func.count())
        .select_from(EscrowRelease)
        .where(EscrowRelease.milestone_id == funded.foundation.id)
    )
    assert count == 1


async def test_running_the_task_twice_releases_once(
    db_session: AsyncSession, queued: Queued, paystack: FakePaystack
) -> None:
    funded = await approved(db_session)
    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    factory = session_factory(db_session)
    assert await escrow_tasks.run_submit_release(factory, result.release_id, retries=0) == "done"
    assert await escrow_tasks.run_submit_release(factory, result.release_id, retries=0) == "done"
    assert len(await entries_of_release(db_session, result.release_id)) == 2  # one transaction
    assert len(queued.payouts) == 1
    assert (await simulated_escrow().balance(funded.project.id)).released_minor == FOUNDATION_NGN


# --- refusals -----------------------------------------------------------------------------------


async def test_only_an_approved_milestone_can_be_released(db_session: AsyncSession, queued: Queued) -> None:
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)  # funded, not approved
    with pytest.raises(AppError) as err:
        await escrow.request_release(db_session, funded.foundation.id, funded.client)
    assert (err.value.code, err.value.status_code) == ("milestone_not_approved", 409)


async def approve_without_hold(db_session: AsyncSession, funded: Funded, milestone: Milestone) -> None:
    """Approved, but no money of its own held (e.g. funded before escrow_holds existed)."""
    await milestones.mark_funded(db_session, milestone.id)
    await approve_milestone(db_session, funded, milestone)


async def test_no_held_money_is_refused(db_session: AsyncSession, queued: Queued) -> None:
    funded = await make_active_project(db_session)
    await approve_without_hold(db_session, funded, funded.foundation)
    with pytest.raises(AppError) as err:
        await escrow.request_release(db_session, funded.foundation.id, funded.client)
    assert (err.value.code, err.value.status_code) == ("escrow_hold_missing", 409)
    assert queued.releases == []


async def test_not_enough_left_in_escrow_is_refused(db_session: AsyncSession, queued: Queued) -> None:
    funded = await approved(db_session)
    # Blockwork is approved too, but its own money was never held, and foundation's hold is spoken for.
    await escrow.request_release(db_session, funded.foundation.id, funded.client)
    await approve_without_hold(db_session, funded, funded.blockwork)
    with pytest.raises(AppError) as err:
        await escrow.request_release(db_session, funded.blockwork.id, funded.client)
    assert (err.value.code, err.value.status_code) == ("escrow_insufficient_funds", 409)
    assert BLOCKWORK_NGN < FOUNDATION_NGN  # it would have fitted in the hold had it been free


# --- retries --------------------------------------------------------------------------------


async def test_partner_down_twice_then_up_releases_once(
    db_session: AsyncSession, queued: Queued, paystack: FakePaystack
) -> None:
    funded = await approved(db_session)
    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    factory = session_factory(db_session)
    simulated_escrow().fail_next("release", times=2)

    assert await escrow_tasks.run_submit_release(factory, result.release_id, retries=0) == "retry"
    assert await escrow_tasks.run_submit_release(factory, result.release_id, retries=1) == "retry"
    assert (await escrow.get_release(db_session, result.release_id)).status == "requested"
    assert await escrow_tasks.run_submit_release(factory, result.release_id, retries=2) == "done"

    assert (await escrow.get_release(db_session, result.release_id)).status == "released"
    assert len(await entries_of_release(db_session, result.release_id)) == 2
    assert await milestone_status(db_session, funded.foundation) == MilestoneStatus.RELEASED


async def test_partner_down_after_three_retries_fails_and_alerts_ops(
    db_session: AsyncSession, queued: Queued, caplog: pytest.LogCaptureFixture
) -> None:
    funded = await approved(db_session)
    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    factory = session_factory(db_session)
    simulated_escrow().fail_next("release", times=4)

    outcomes = [
        await escrow_tasks.run_submit_release(factory, result.release_id, retries=n) for n in range(4)
    ]
    assert outcomes == ["retry", "retry", "retry", "gave_up"]

    release = await escrow.get_release(db_session, result.release_id)
    assert release.status == "failed"
    assert release.failure_reason and "4 tries" in release.failure_reason
    assert await actions(db_session, release.id) == ["escrow.release_requested", "escrow.release_failed"]
    assert "OPS ALERT" in caplog.text
    assert await milestone_status(db_session, funded.foundation) == MilestoneStatus.APPROVED
    assert await all_entries_for_release_count(db_session, release.id) == 0
    assert [r.id for r in await escrow.list_failed_releases(db_session)] == [release.id]


async def all_entries_for_release_count(db_session: AsyncSession, release_id: uuid.UUID) -> int:
    return len(await entries_of_release(db_session, release_id))


def test_celery_task_retries_with_backoff_then_returns(monkeypatch: pytest.MonkeyPatch) -> None:
    outcomes = iter(["retry", "retry", "done"])
    seen: list[int] = []

    async def fake_run(factory: object, release_id: uuid.UUID, retries: int) -> str:
        seen.append(retries)
        return next(outcomes)

    monkeypatch.setattr(escrow_tasks, "run_submit_release", fake_run)
    monkeypatch.setattr(escrow_tasks, "retry_delay", lambda retries: 0)
    result = escrow_tasks.submit_release_task.apply(args=[str(uuid.uuid4())])
    assert seen == [0, 1, 2]
    assert result.get() == "done"


# --- partner confirms later, by webhook -------------------------------------------------------


class _SubmittingEscrow:
    """A partner that accepts the release now and confirms it by webhook later."""

    async def release(self, hold_ref: str, payee: str, amount_minor: int, ref: str) -> ReleaseResult:
        return ReleaseResult(f"partner_{ref}", "submitted", hold_ref, payee, amount_minor, "NGN", ref)


async def test_submitted_release_is_confirmed_by_webhook_once(
    client: AsyncClient,
    db_session: AsyncSession,
    queued: Queued,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    funded = await approved(db_session)
    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    monkeypatch.setattr(escrow, "get_escrow_provider", lambda: _SubmittingEscrow())
    assert await escrow_tasks.run_submit_release(session_factory(db_session), result.release_id, 0) == "done"
    release = await escrow.get_release(db_session, result.release_id)
    assert (release.status, release.provider_ref) == ("submitted", f"partner_{release.id}")
    assert await milestone_status(db_session, funded.foundation) == MilestoneStatus.APPROVED

    event = release_event(
        "release.succeeded", release.id, provider_ref=release.provider_ref, amount_minor=FOUNDATION_NGN
    )
    first = await send_escrow(client, event)
    again = await send_escrow(client, event)
    assert (first.status_code, first.json()["duplicate"]) == (200, False)
    assert (again.status_code, again.json()["duplicate"]) == (200, True)

    await db_session.refresh(release)
    assert release.status == "released"
    assert await milestone_status(db_session, funded.foundation) == MilestoneStatus.RELEASED
    assert len(await entries_of_release(db_session, release.id)) == 2
    assert len(queued.payouts) == 1


async def test_failed_release_webhook_fails_it(
    client: AsyncClient, db_session: AsyncSession, queued: Queued, monkeypatch: pytest.MonkeyPatch
) -> None:
    funded = await approved(db_session)
    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    monkeypatch.setattr(escrow, "get_escrow_provider", lambda: _SubmittingEscrow())
    await escrow_tasks.run_submit_release(session_factory(db_session), result.release_id, 0)

    response = await send_escrow(
        client, release_event("release.failed", result.release_id, reason="KYC hold")
    )
    assert response.status_code == 200
    release = await escrow.get_release(db_session, result.release_id)
    assert (release.status, release.failure_reason) == ("failed", "KYC hold")
    assert await entries_of_release(db_session, release.id) == []


async def test_webhook_with_a_different_amount_is_not_applied(
    client: AsyncClient, db_session: AsyncSession, queued: Queued, monkeypatch: pytest.MonkeyPatch
) -> None:
    funded = await approved(db_session)
    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    monkeypatch.setattr(escrow, "get_escrow_provider", lambda: _SubmittingEscrow())
    await escrow_tasks.run_submit_release(session_factory(db_session), result.release_id, 0)

    response = await send_escrow(
        client, release_event("release.succeeded", result.release_id, amount_minor=1)
    )
    assert response.status_code == 200
    assert (await escrow.get_release(db_session, result.release_id)).status == "submitted"


async def test_webhook_for_an_unknown_release_is_acknowledged(client: AsyncClient) -> None:
    response = await send_escrow(client, release_event("release.succeeded", uuid.uuid4()))
    assert response.status_code == 200


# --- the contractor's payout ------------------------------------------------------------------


async def released(db_session: AsyncSession, queued: Queued, **kwargs: bool) -> tuple[Funded, EscrowRelease]:
    funded = await approved(db_session, **kwargs)
    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    await escrow_tasks.run_submit_release(session_factory(db_session), result.release_id, retries=0)
    return funded, await escrow.get_release(db_session, result.release_id)


async def test_contractor_without_a_bank_account_is_left_for_ops(
    db_session: AsyncSession, queued: Queued, caplog: pytest.LogCaptureFixture
) -> None:
    _, release = await released(db_session, queued, recipient=False)
    assert release.status == "released"  # the money left escrow; paying it out waits for ops
    assert await payout_of(db_session, release.id) is None
    assert "payout.awaiting_recipient" in await actions(db_session, release.id)
    assert "OPS ALERT" in caplog.text


async def test_paystack_lost_answer_is_recovered_by_reference(
    db_session: AsyncSession, queued: Queued, paystack: FakePaystack
) -> None:
    _, release = await released(db_session, queued)
    payout = await payout_of(db_session, release.id)
    assert payout is not None
    factory = session_factory(db_session)

    # Try 1: the answer is lost, and Paystack can't say yet whether it has the transfer.
    paystack.initiate_answers.append(AppError("paystack_unavailable", "timed out", 502))
    paystack.verify_answers.append(None)
    assert await payments_tasks.run_send_transfer(factory, payout.id, retries=0) == "retry"
    await db_session.refresh(payout)
    assert (payout.status, payout.provider_transfer_code) == ("pending", None)  # the row survived

    # Try 2: Paystack refuses the used reference; looking it up shows the first try went through.
    paystack.initiate_answers.append(AppError("paystack_refused", "Duplicate Transfer Reference", 422))
    paystack.verify_answers.append(TransferResult(payout.reference, "TRF_first", "success"))
    assert await payments_tasks.run_send_transfer(factory, payout.id, retries=1) == "done"

    await db_session.refresh(payout)
    assert (payout.status, payout.provider_transfer_code) == ("success", "TRF_first")
    assert paystack.initiated == [payout.reference, payout.reference]
    assert await balance(db_session, accounts.contractor_payable("NGN")) == 0  # listener ran
    assert await balance(db_session, accounts.escrow_payouts("NGN")) == FOUNDATION_NGN

    # A third run (say, the sweeper) does nothing.
    assert await payments_tasks.run_send_transfer(factory, payout.id, retries=0) == "done"
    assert len(paystack.initiated) == 2


async def test_paystack_refusing_a_new_transfer_fails_the_payout(
    db_session: AsyncSession, queued: Queued, paystack: FakePaystack, caplog: pytest.LogCaptureFixture
) -> None:
    _, release = await released(db_session, queued)
    payout = await payout_of(db_session, release.id)
    assert payout is not None
    paystack.initiate_answers.append(AppError("paystack_refused", "Insufficient balance", 422))
    paystack.verify_answers.append(None)
    assert await payments_tasks.run_send_transfer(session_factory(db_session), payout.id, retries=0) == "done"
    await db_session.refresh(payout)
    assert (payout.status, payout.failure_reason) == ("failed", "Insufficient balance")
    assert await balance(db_session, accounts.contractor_payable("NGN")) == FOUNDATION_NGN  # still owed
    assert "escrow.payout_failed" in await actions(db_session, release.id)
    assert "OPS ALERT" in caplog.text


async def test_paystack_down_for_every_try_alerts_ops(
    db_session: AsyncSession, queued: Queued, paystack: FakePaystack, caplog: pytest.LogCaptureFixture
) -> None:
    _, release = await released(db_session, queued)
    payout = await payout_of(db_session, release.id)
    assert payout is not None
    down = AppError("paystack_unavailable", "down", 502)
    paystack.initiate_answers.extend([down, down])
    outcome = await payments_tasks.run_send_transfer(
        session_factory(db_session), payout.id, retries=1, max_retries=1
    )
    assert outcome == "gave_up"
    assert "payout.send_failed" in await actions(db_session, payout.id)
    assert "OPS ALERT" in caplog.text


async def test_reversed_payout_moves_the_money_back_to_payable(
    client: AsyncClient, db_session: AsyncSession, queued: Queued, paystack: FakePaystack
) -> None:
    _, release = await released(db_session, queued)
    payout = await payout_of(db_session, release.id)
    assert payout is not None
    await payments_tasks.run_send_transfer(session_factory(db_session), payout.id, retries=0)
    await db_session.refresh(payout)
    assert (await send_paystack(client, transfer_event("transfer.success", payout))).status_code == 200
    assert (await send_paystack(client, transfer_event("transfer.reversed", payout))).status_code == 200

    assert await balance(db_session, accounts.contractor_payable("NGN")) == FOUNDATION_NGN
    assert await balance(db_session, accounts.escrow_payouts("NGN")) == 0
    assert unbalanced(await all_entries(db_session)) == {}
    assert (await actions(db_session, release.id))[-1] == "escrow.payout_reversed"


# --- the sweeper ------------------------------------------------------------------------------


async def test_sweeper_requeues_stale_requests_only(db_session: AsyncSession, queued: Queued) -> None:
    funded = await approved(db_session)
    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    release = await escrow.get_release(db_session, result.release_id)
    factory = session_factory(db_session)

    assert await escrow_tasks.run_sweep(factory) == (0, 0)  # just requested: its own task is coming
    later = release.updated_at + escrow.STALE_REQUEST * 2
    assert await escrow_tasks.run_sweep(factory, now=later) == (1, 0)
    assert queued.releases[-1] == release.id
