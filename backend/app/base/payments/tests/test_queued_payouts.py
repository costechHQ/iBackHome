"""Payouts saved before Paystack is called: after-commit queueing, queue_transfer, and looking a
transfer up by reference when Paystack's answer was lost. HTTP is mocked with respx."""

import uuid
from collections.abc import Iterator

import httpx
import pytest
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import queue_transfer
from app.base.payments import service as payments_service
from app.base.payments.after_commit import after_commit
from app.base.payments.paystack import HttpPaystackClient
from app.base.payments.tests.webhook_helpers import PAYSTACK_SECRET
from app.core.errors import AppError
from app.features.escrow.tests.release_helpers import add_recipient
from app.features.projects.tests.factories import make_user

API = "https://api.paystack.co"
REFERENCE = "rel_" + "a" * 32


@pytest.fixture
def paystack_http() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=API, assert_all_called=False) as router:
        yield router


def http_client() -> HttpPaystackClient:
    return HttpPaystackClient(PAYSTACK_SECRET, API)


# --- after_commit ---------------------------------------------------------------------------


async def test_callbacks_run_only_after_commit(db_session: AsyncSession) -> None:
    ran: list[int] = []
    after_commit(db_session, ran.append, 1)
    await db_session.flush()
    assert ran == []
    await db_session.commit()
    assert ran == [1]
    await db_session.commit()
    assert ran == [1]  # once


async def test_rollback_drops_callbacks(db_session: AsyncSession) -> None:
    ran: list[int] = []
    after_commit(db_session, ran.append, 1)
    await db_session.rollback()
    await db_session.commit()
    assert ran == []


async def test_a_caught_savepoint_failure_keeps_earlier_callbacks(db_session: AsyncSession) -> None:
    ran: list[int] = []
    after_commit(db_session, ran.append, 1)
    with pytest.raises(RuntimeError):
        async with db_session.begin_nested():
            raise RuntimeError("inner step failed")
    await db_session.commit()
    assert ran == [1]


async def test_a_failing_callback_does_not_break_the_others(db_session: AsyncSession) -> None:
    ran: list[int] = []

    def boom(_: int) -> None:
        raise RuntimeError("queue down")

    after_commit(db_session, boom, 0)
    after_commit(db_session, ran.append, 2)
    await db_session.commit()
    assert ran == [2]


# --- queue_transfer -------------------------------------------------------------------------


async def test_queue_transfer_saves_a_pending_payout_and_queues_it_after_commit(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    queued: list[uuid.UUID] = []
    monkeypatch.setattr(payments_service, "enqueue_send_transfer", queued.append)
    contractor = await make_user(db_session, "contractor")
    recipient = await add_recipient(db_session, user_id=contractor.id)

    payout = await queue_transfer(db_session, recipient.id, 5_000_000, REFERENCE, reason="Milestone 1")
    assert (payout.status, payout.provider_transfer_code) == ("pending", None)
    again = await queue_transfer(db_session, recipient.id, 5_000_000, REFERENCE, reason="Milestone 1")
    assert again.id == payout.id
    with pytest.raises(AppError) as err:
        await queue_transfer(db_session, recipient.id, 1, REFERENCE, reason="Milestone 1")
    assert err.value.code == "payout_reference_conflict"

    assert queued == []
    await db_session.commit()
    assert queued == [payout.id]


@pytest.mark.parametrize("amount", [0, -1, True])
async def test_queue_transfer_refuses_bad_amounts(db_session: AsyncSession, amount: int) -> None:
    contractor = await make_user(db_session, "contractor")
    recipient = await add_recipient(db_session, user_id=contractor.id)
    with pytest.raises(AppError) as err:
        await queue_transfer(db_session, recipient.id, amount, REFERENCE, reason="x")
    assert err.value.code == "invalid_amount"


async def test_get_recipient_for_needs_exactly_one_owner(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as err:
        await payments_service.get_recipient_for(db_session)
    assert err.value.code == "recipient_owner_required"
    assert await payments_service.get_recipient_for(db_session, user_id=uuid.uuid4()) is None


# --- verify_transfer over HTTP ----------------------------------------------------------------


async def test_verify_finds_the_transfer(paystack_http: respx.MockRouter) -> None:
    paystack_http.get(f"/transfer/verify/{REFERENCE}").respond(
        200,
        json={
            "status": True,
            "message": "Transfer retrieved",
            "data": {"reference": REFERENCE, "transfer_code": "TRF_abc", "status": "success"},
        },
    )
    result = await http_client().verify_transfer(REFERENCE)
    assert result is not None
    assert (result.transfer_code, result.status) == ("TRF_abc", "success")


async def test_verify_says_none_when_paystack_never_had_it(paystack_http: respx.MockRouter) -> None:
    paystack_http.get(f"/transfer/verify/{REFERENCE}").respond(
        404, json={"status": False, "message": "Transfer not found"}
    )
    assert await http_client().verify_transfer(REFERENCE) is None


async def test_verify_while_paystack_is_down_raises_unavailable(paystack_http: respx.MockRouter) -> None:
    paystack_http.get(f"/transfer/verify/{REFERENCE}").mock(side_effect=httpx.ConnectTimeout("slow"))
    with pytest.raises(AppError) as err:
        await http_client().verify_transfer(REFERENCE)
    assert err.value.code == "paystack_unavailable"
