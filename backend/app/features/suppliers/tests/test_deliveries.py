import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.core.errors import AppError
from app.features.evidence.models import Evidence
from app.features.evidence.tests.conftest import World, add_evidence, bearer, make_user, make_world
from app.features.suppliers import escrow_bridge, service
from app.features.suppliers.models import Delivery, MaterialOrder, Supplier
from app.features.suppliers.schemas import DeliveryItem, OrderItem

CEMENT = OrderItem(item="Cement", unit="bag", quantity="100", unit_price_minor=780_000)  # type: ignore[arg-type]
SAND = OrderItem(item="Sharp sand", unit="tonne", quantity="2.5", unit_price_minor=1_500_000)  # type: ignore[arg-type]
COUNTED = [{"item": "Cement", "quantity": "100"}, {"item": "Sharp sand", "quantity": "2.5"}]


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    return await make_world(db_session)


@pytest.fixture
async def paid_calls(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    """Stands in for Gabriel's escrow.pay_supplier and records the orders it was asked to pay."""
    calls: list[uuid.UUID] = []

    async def fake(session: AsyncSession, order_id: uuid.UUID) -> None:
        calls.append(order_id)

    monkeypatch.setattr(escrow_bridge, "pay_supplier", fake)
    return calls


async def approved_order(
    db_session: AsyncSession, world: World, items: list[OrderItem] | None = None
) -> MaterialOrder:
    supplier = Supplier(name="Enugu Building Supplies", verified=True)
    db_session.add(supplier)
    await db_session.flush()
    order = await service.request_order(
        db_session, world.contractor, world.project.id, supplier.id, items or [CEMENT, SAND]
    )
    return await service.approve_order(db_session, world.client, order.id)


async def good_photo(db_session: AsyncSession, world: World) -> Evidence:
    row: Evidence = await add_evidence(db_session, world, status="accepted", role="supervisor")
    return row


async def confirm(
    client: AsyncClient,
    order: MaterialOrder,
    who: Any,
    evidence: list[Evidence],
    counted: list[dict[str, str]] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> Any:
    return await client.post(
        f"/api/v1/orders/{order.id}/delivery",
        json={"quantities": counted or COUNTED, "evidence_ids": [str(e.id) for e in evidence]},
        headers=bearer(who) | (extra_headers or {}),
    )


# the happy path: delivered, audited, and the supplier payment is started


async def test_supervisor_confirms_a_delivery_and_payment_starts(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    photo = await good_photo(db_session, world)
    response = await confirm(client, order, world.supervisor, [photo])
    assert response.status_code == 201
    out = response.json()
    assert out["order_id"] == str(order.id)
    assert out["confirmed_by"] == str(world.supervisor.id)
    assert out["evidence_ids"] == [str(photo.id)]
    assert {q["item"]: q["quantity"] for q in out["quantities"]} == {"Cement": "100", "Sharp sand": "2.5"}

    await db_session.refresh(order)
    assert order.status == "delivered"
    assert paid_calls == [order.id]  # pay_supplier called exactly once, for this order
    entry = await db_session.scalar(
        select(AuditEntry).where(AuditEntry.object_id == order.id, AuditEntry.action == "order.delivered")
    )
    assert entry is not None and entry.actor_id == world.supervisor.id
    assert entry.before is not None and entry.before["status"] == "approved"
    assert entry.after is not None and entry.after["status"] == "delivered"


async def test_the_same_amount_written_differently_still_matches(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    counted = [{"item": "Cement", "quantity": "100.000"}, {"item": "Sharp sand", "quantity": "2.50"}]
    response = await confirm(client, order, world.supervisor, [await good_photo(db_session, world)], counted)
    assert response.status_code == 201


async def test_two_photos_and_a_repeated_id_are_stored_once(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    a, b = await good_photo(db_session, world), await good_photo(db_session, world)
    response = await confirm(client, order, world.supervisor, [a, b, a])
    assert response.status_code == 201
    assert response.json()["evidence_ids"] == [str(a.id), str(b.id)]


# the payment must be started, or nothing is saved


async def test_without_a_connected_payment_the_delivery_is_refused(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    order = await approved_order(db_session, world)
    photo = await good_photo(db_session, world)
    response = await confirm(client, order, world.supervisor, [photo])  # the real bridge: not connected yet
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "escrow_not_ready"


async def test_a_failed_payment_start_undoes_the_delivery(
    db_session: AsyncSession, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing(session: AsyncSession, order_id: uuid.UUID) -> None:
        raise AppError("escrow_down", "The escrow partner is down.", 503)

    monkeypatch.setattr(escrow_bridge, "pay_supplier", failing)
    order = await approved_order(db_session, world)
    photo = await good_photo(db_session, world)
    with pytest.raises(AppError):
        async with db_session.begin_nested():  # what the request's rolled-back transaction does
            await service.confirm_delivery(
                db_session,
                world.supervisor,
                order.id,
                [
                    DeliveryItem(item="Cement", quantity=Decimal("100")),
                    DeliveryItem(item="Sharp sand", quantity=Decimal("2.5")),
                ],
                [photo.id],
            )
    await db_session.refresh(order)
    assert order.status == "approved"
    assert await db_session.scalar(select(Delivery).where(Delivery.order_id == order.id)) is None


# the quantities must match the order


@pytest.mark.parametrize(
    "counted",
    [
        [{"item": "Cement", "quantity": "99"}, {"item": "Sharp sand", "quantity": "2.5"}],  # short
        [{"item": "Cement", "quantity": "101"}, {"item": "Sharp sand", "quantity": "2.5"}],  # over
        [{"item": "Cement", "quantity": "100"}],  # an item missing
        [*COUNTED, {"item": "Gravel", "quantity": "1"}],  # an item that was not ordered
        [{"item": "Cement", "quantity": "100"}, {"item": "Sand", "quantity": "2.5"}],  # a renamed item
    ],
)
async def test_quantities_that_differ_from_the_order_are_refused(
    client: AsyncClient,
    db_session: AsyncSession,
    world: World,
    paid_calls: list[uuid.UUID],
    counted: list[dict[str, str]],
) -> None:
    order = await approved_order(db_session, world)
    response = await confirm(client, order, world.supervisor, [await good_photo(db_session, world)], counted)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "quantity_mismatch"
    assert paid_calls == []
    await db_session.refresh(order)
    assert order.status == "approved"


# the evidence must be real accepted supervisor evidence on this project


async def test_each_kind_of_unsuitable_evidence_is_refused(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    other = await make_world(db_session)
    unsuitable = {
        "pending": await add_evidence(db_session, world, status="pending_checks"),
        "flagged": await add_evidence(db_session, world, status="flagged"),
        "rejected": await add_evidence(db_session, world, status="rejected"),
        "contractor's": await add_evidence(db_session, world, status="accepted", role="contractor"),
        "another project's": await add_evidence(db_session, other, status="accepted"),
    }
    for name, photo in unsuitable.items():
        response = await confirm(client, order, world.supervisor, [photo])
        assert response.status_code == 422, name
        assert response.json()["error"]["code"] == "evidence_not_accepted", name
    ghost = await client.post(
        f"/api/v1/orders/{order.id}/delivery",
        json={"quantities": COUNTED, "evidence_ids": [str(uuid.uuid4())]},
        headers=bearer(world.supervisor),
    )
    assert ghost.status_code == 422
    assert paid_calls == []


async def test_one_bad_photo_among_good_ones_refuses_the_delivery(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    good = await good_photo(db_session, world)
    bad = await add_evidence(db_session, world, status="flagged")
    assert (await confirm(client, order, world.supervisor, [good, bad])).status_code == 422


async def test_at_least_one_photo_is_required(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    response = await confirm(client, order, world.supervisor, [])
    assert response.status_code == 422
    assert paid_calls == []


# who and when


async def test_only_the_projects_supervisor_can_confirm(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    photo = await good_photo(db_session, world)
    other_supervisor = await make_user(db_session, "supervisor")
    response = await confirm(client, order, other_supervisor, [photo])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"
    for who in (world.contractor, world.client, world.ops):
        assert (await confirm(client, order, who, [photo])).status_code == 403
    signed_out = await client.post(
        f"/api/v1/orders/{order.id}/delivery", json={"quantities": COUNTED, "evidence_ids": [str(photo.id)]}
    )
    assert signed_out.status_code == 401
    assert paid_calls == []


async def test_a_member_who_is_a_different_supervisor_is_not_the_assigned_one(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    photo = await good_photo(db_session, world)
    world.project.supervisor_id = (await make_user(db_session, "supervisor")).id  # replaced
    await db_session.flush()
    response = await confirm(client, order, world.supervisor, [photo])
    assert response.status_code == 403


async def test_only_an_approved_order_can_be_delivered(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    supplier = Supplier(name="S", verified=True)
    db_session.add(supplier)
    await db_session.flush()
    requested = await service.request_order(
        db_session, world.contractor, world.project.id, supplier.id, [CEMENT, SAND]
    )
    photo = await good_photo(db_session, world)
    response = await confirm(client, requested, world.supervisor, [photo])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_order_transition"
    assert paid_calls == []


async def test_a_delivery_cannot_be_confirmed_twice(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    photo = await good_photo(db_session, world)
    first = await confirm(client, order, world.supervisor, [photo])
    second = await confirm(client, order, world.supervisor, [photo])
    assert first.status_code == 201
    assert second.status_code == 409
    assert paid_calls == [order.id]  # the supplier is paid once, not twice


async def test_a_retry_with_the_same_idempotency_key_replays_without_paying_twice(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    photo = await good_photo(db_session, world)
    first = await confirm(
        client, order, world.supervisor, [photo], extra_headers={"Idempotency-Key": "deliver-1"}
    )
    second = await confirm(
        client, order, world.supervisor, [photo], extra_headers={"Idempotency-Key": "deliver-1"}
    )
    assert first.status_code == second.status_code == 201
    assert second.json() == first.json()
    assert paid_calls == [order.id]


async def test_unknown_order_is_404(client: AsyncClient, db_session: AsyncSession, world: World) -> None:
    photo = await good_photo(db_session, world)
    response = await client.post(
        f"/api/v1/orders/{uuid.uuid4()}/delivery",
        json={"quantities": COUNTED, "evidence_ids": [str(photo.id)]},
        headers=bearer(world.supervisor),
    )
    assert response.status_code == 404


# delivered -> paid, called by the payments code once the supplier is paid


async def test_mark_paid_moves_a_delivered_order_to_paid(
    client: AsyncClient, db_session: AsyncSession, world: World, paid_calls: list[uuid.UUID]
) -> None:
    order = await approved_order(db_session, world)
    await confirm(client, order, world.supervisor, [await good_photo(db_session, world)])
    paid = await service.mark_paid(db_session, order.id)
    assert paid.status == "paid"
    entry = await db_session.scalar(
        select(AuditEntry).where(AuditEntry.object_id == order.id, AuditEntry.action == "order.paid")
    )
    assert entry is not None and entry.actor_id is None  # the system


async def test_mark_paid_only_works_on_a_delivered_order(db_session: AsyncSession, world: World) -> None:
    order = await approved_order(db_session, world)  # approved, not delivered
    with pytest.raises(AppError) as err:
        await service.mark_paid(db_session, order.id)
    assert err.value.status_code == 409
    with pytest.raises(AppError) as missing:
        await service.mark_paid(db_session, uuid.uuid4())
    assert missing.value.status_code == 404
