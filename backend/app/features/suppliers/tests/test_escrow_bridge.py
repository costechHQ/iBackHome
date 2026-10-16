"""The bridge to Gabriel's escrow: a delivered order really starts the supplier's payment."""

from collections.abc import Iterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.escrow import service as escrow
from app.features.escrow.tests.factories import Funded, make_active_project, simulated_escrow
from app.features.escrow.tests.release_helpers import Queued, add_recipient, hold_milestone
from app.features.suppliers import escrow_bridge
from app.features.suppliers.models import MaterialOrder, Supplier

CEMENT_ORDER = 78_000_000  # 100 bags at ₦7,800


@pytest.fixture(autouse=True)
def _fresh_escrow() -> Iterator[None]:
    simulated_escrow().reset()
    yield
    simulated_escrow().reset()


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> Queued:
    spy = Queued()
    monkeypatch.setattr(escrow, "enqueue_submit_release", spy.releases.append)
    return spy


async def delivered_order(session: AsyncSession, funded: Funded) -> MaterialOrder:
    supplier = Supplier(name="Enugu Building Supplies", verified=True)
    session.add(supplier)
    await session.flush()
    order = MaterialOrder(
        project_id=funded.project.id,
        supplier_id=supplier.id,
        requested_by=funded.contractor.id,
        items=[{"item": "Cement", "unit": "bag", "quantity": "100", "unit_price_minor": 780_000}],
        total_minor=CEMENT_ORDER,
        currency="NGN",
        status="delivered",
    )
    session.add(order)
    await session.flush()
    return order


async def test_delivered_order_starts_the_supplier_release(db_session: AsyncSession, queued: Queued) -> None:
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)
    order = await delivered_order(db_session, funded)
    await add_recipient(db_session, supplier_id=order.supplier_id)

    await escrow_bridge.pay_supplier(db_session, order.id)
    await db_session.commit()

    [release_id] = queued.releases  # submitted to the escrow partner after commit
    release = await escrow.get_release(db_session, release_id)
    assert (release.payee, release.amount_minor, release.order_id) == (
        f"supplier:{order.supplier_id}",
        CEMENT_ORDER,
        order.id,
    )


async def test_escrow_refusal_reaches_the_caller(db_session: AsyncSession, queued: Queued) -> None:
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)
    order = await delivered_order(db_session, funded)  # no bank account registered

    with pytest.raises(AppError) as err:
        await escrow_bridge.pay_supplier(db_session, order.id)
    assert (err.value.code, err.value.status_code) == ("supplier_payout_not_set", 409)
    assert queued.releases == []
