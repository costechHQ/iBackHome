"""Paying a supplier for a delivered order: pay_supplier -> released from the project's escrow ->
supplier payout -> order paid (Abigail's suppliers.mark_paid)."""

import uuid
from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import accounts, balance
from app.base.payments import service as payments_service
from app.base.payments import tasks as payments_tasks
from app.base.payments.models import Payout
from app.base.payments.tests.webhook_helpers import webhook_secrets
from app.core.errors import AppError
from app.features.escrow import service as escrow
from app.features.escrow import tasks as escrow_tasks
from app.features.escrow.tests.factories import FOUNDATION_NGN, Funded, make_active_project, simulated_escrow
from app.features.escrow.tests.release_helpers import (
    FakePaystack,
    Queued,
    add_recipient,
    all_entries,
    approve_milestone,
    entries_of_release,
    hold_milestone,
    send_paystack,
    session_factory,
    transfer_event,
    unbalanced,
)
from app.features.suppliers.models import MaterialOrder, Supplier

CEMENT_ORDER = 78_000_000  # 100 bags at ₦7,800


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


async def delivered_order(
    db_session: AsyncSession, funded: Funded, *, total_minor: int = CEMENT_ORDER, status: str = "delivered"
) -> MaterialOrder:
    supplier = Supplier(name="Enugu Building Supplies", verified=True)
    db_session.add(supplier)
    await db_session.flush()
    order = MaterialOrder(
        project_id=funded.project.id,
        supplier_id=supplier.id,
        requested_by=funded.contractor.id,
        items=[{"item": "Cement", "unit": "bag", "quantity": "100", "unit_price_minor": 780_000}],
        total_minor=total_minor,
        currency="NGN",
        status=status,
    )
    db_session.add(order)
    await db_session.flush()
    return order


async def held_project(db_session: AsyncSession) -> Funded:
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)
    return funded


async def test_delivered_order_ends_paid_with_balanced_entries(
    client: AsyncClient, db_session: AsyncSession, queued: Queued, paystack: FakePaystack
) -> None:
    funded = await held_project(db_session)
    order = await delivered_order(db_session, funded)
    await add_recipient(db_session, supplier_id=order.supplier_id)
    factory = session_factory(db_session)

    release_id = await escrow.pay_supplier(db_session, order.id)
    assert await escrow.pay_supplier(db_session, order.id) == release_id  # idempotent
    await db_session.commit()
    assert queued.releases == [release_id]

    assert await escrow_tasks.run_submit_release(factory, release_id, retries=0) == "done"
    release = await escrow.get_release(db_session, release_id)
    assert (release.status, release.payee, release.milestone_id) == (
        "released",
        f"supplier:{order.supplier_id}",
        None,
    )
    p = funded.project.id
    assert await balance(db_session, accounts.escrow(p, "NGN")) == FOUNDATION_NGN - CEMENT_ORDER
    assert await balance(db_session, accounts.supplier_payable("NGN")) == CEMENT_ORDER
    await db_session.refresh(order)
    assert order.status == "delivered"  # paid only once the money reaches the supplier

    payout = await db_session.scalar(
        select(Payout).where(Payout.reference == escrow.payout_reference(release_id))
    )
    assert payout is not None and payout.amount_minor == CEMENT_ORDER
    await payments_tasks.run_send_transfer(factory, payout.id, retries=0)
    await db_session.refresh(payout)
    assert (await send_paystack(client, transfer_event("transfer.success", payout))).status_code == 200

    await db_session.refresh(order)
    assert order.status == "paid"
    assert await balance(db_session, accounts.supplier_payable("NGN")) == 0
    assert await balance(db_session, accounts.escrow_payouts("NGN")) == CEMENT_ORDER
    assert len(await entries_of_release(db_session, release_id)) == 4
    assert unbalanced(await all_entries(db_session)) == {}


async def test_supplier_without_a_bank_account_is_refused(db_session: AsyncSession, queued: Queued) -> None:
    funded = await held_project(db_session)
    order = await delivered_order(db_session, funded)
    with pytest.raises(AppError) as err:
        await escrow.pay_supplier(db_session, order.id)
    assert (err.value.code, err.value.status_code) == ("supplier_payout_not_set", 409)
    assert queued.releases == []


async def test_order_that_is_not_delivered_is_refused(db_session: AsyncSession, queued: Queued) -> None:
    funded = await held_project(db_session)
    order = await delivered_order(db_session, funded, status="approved")
    await add_recipient(db_session, supplier_id=order.supplier_id)
    with pytest.raises(AppError) as err:
        await escrow.pay_supplier(db_session, order.id)
    assert (err.value.code, err.value.status_code) == ("order_not_delivered", 409)


async def test_unknown_order_is_404(db_session: AsyncSession, queued: Queued) -> None:
    with pytest.raises(AppError) as err:
        await escrow.pay_supplier(db_session, uuid.uuid4())
    assert err.value.status_code == 404


async def test_order_bigger_than_what_is_left_is_refused(db_session: AsyncSession, queued: Queued) -> None:
    funded = await held_project(db_session)
    order = await delivered_order(db_session, funded, total_minor=FOUNDATION_NGN + 1)
    await add_recipient(db_session, supplier_id=order.supplier_id)
    with pytest.raises(AppError) as err:
        await escrow.pay_supplier(db_session, order.id)
    assert (err.value.code, err.value.status_code) == ("escrow_insufficient_funds", 409)


async def test_supplier_payment_leaves_too_little_for_the_milestone(
    db_session: AsyncSession, queued: Queued
) -> None:
    """Both draw on the same held money; the second to ask is refused rather than over-released."""
    funded = await held_project(db_session)
    order = await delivered_order(db_session, funded)
    await add_recipient(db_session, supplier_id=order.supplier_id)
    await escrow.pay_supplier(db_session, order.id)
    await approve_milestone(db_session, funded, funded.foundation)
    with pytest.raises(AppError) as err:
        await escrow.request_release(db_session, funded.foundation.id, funded.client)
    assert err.value.code == "escrow_insufficient_funds"
