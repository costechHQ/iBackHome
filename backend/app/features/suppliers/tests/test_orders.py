import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.features.evidence.tests.conftest import World, bearer, make_user, make_world
from app.features.suppliers import service
from app.features.suppliers.models import MaterialOrder, Supplier
from app.features.suppliers.schemas import OrderItem

CEMENT = {"item": "Cement", "unit": "bag", "quantity": "100", "unit_price_minor": 780_000}
SAND = {"item": "Sharp sand", "unit": "tonne", "quantity": "2.5", "unit_price_minor": 1_500_000}


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    return await make_world(db_session)


@pytest.fixture
async def supplier(db_session: AsyncSession) -> Supplier:
    row = Supplier(name="Enugu Building Supplies", verified=True)
    db_session.add(row)
    await db_session.flush()
    return row


def order_url(world: World) -> str:
    return f"/api/v1/projects/{world.project.id}/orders"


async def place(client: AsyncClient, world: World, supplier: Supplier, items: list[dict[str, Any]]) -> Any:
    return await client.post(
        order_url(world),
        json={"supplier_id": str(supplier.id), "items": items},
        headers=bearer(world.contractor),
    )


# POST /projects/{id}/orders


async def test_contractor_requests_materials(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    response = await place(client, world, supplier, [CEMENT, SAND])
    assert response.status_code == 201
    out = response.json()
    assert out["status"] == "requested"
    assert out["currency"] == "NGN"  # taken from the project
    assert out["total_minor"] == 100 * 780_000 + 3_750_000  # 78,000,000 + 2.5 x 1,500,000
    assert out["requested_by"] == str(world.contractor.id)
    assert out["items"][1]["quantity"] == "2.5"
    entry = await db_session.scalar(select(AuditEntry).where(AuditEntry.object_id == uuid.UUID(out["id"])))
    assert entry is not None and entry.action == "order.requested"


async def test_total_is_an_integer_rounded_half_up_per_line(
    client: AsyncClient, world: World, supplier: Supplier
) -> None:
    item = {"item": "Nails", "unit": "kg", "quantity": "0.333", "unit_price_minor": 1_005}  # 334.665
    response = await place(client, world, supplier, [item])
    assert response.status_code == 201
    assert response.json()["total_minor"] == 335
    assert isinstance(response.json()["total_minor"], int)


def test_order_total_helper_never_uses_floats() -> None:
    items = [OrderItem(item="x", unit="u", quantity=Decimal("0.1"), unit_price_minor=3)]
    assert service.order_total_minor(items) == 0  # 0.3 rounds down, and the route refuses a zero total
    items = [OrderItem(item="x", unit="u", quantity=Decimal("2.5"), unit_price_minor=3)]
    assert service.order_total_minor(items) == 8  # 7.5 rounds half up


async def test_a_zero_total_is_refused(client: AsyncClient, world: World, supplier: Supplier) -> None:
    tiny = {"item": "Dust", "unit": "kg", "quantity": "0.001", "unit_price_minor": 100}  # 0.1 kobo
    response = await place(client, world, supplier, [tiny])
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_order_total"


@pytest.mark.parametrize(
    "bad_item",
    [
        {**CEMENT, "quantity": "0"},
        {**CEMENT, "quantity": "-1"},
        {**CEMENT, "quantity": "1.2345"},  # more than 3 decimals
        {**CEMENT, "unit_price_minor": 0},
        {**CEMENT, "unit_price_minor": -5},
        {**CEMENT, "unit_price_minor": "12.50"},  # money is whole minor units
        {**CEMENT, "item": ""},
    ],
)
async def test_invalid_items_are_422(
    client: AsyncClient, world: World, supplier: Supplier, bad_item: dict[str, Any]
) -> None:
    response = await place(client, world, supplier, [bad_item])
    assert response.status_code == 422


async def test_an_order_needs_at_least_one_item(
    client: AsyncClient, world: World, supplier: Supplier
) -> None:
    response = await place(client, world, supplier, [])
    assert response.status_code == 422


async def test_unknown_supplier_is_404(client: AsyncClient, world: World) -> None:
    response = await client.post(
        order_url(world),
        json={"supplier_id": str(uuid.uuid4()), "items": [CEMENT]},
        headers=bearer(world.contractor),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "supplier_not_found"


async def test_only_the_projects_contractor_can_request(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    other_contractor = await make_user(db_session, "contractor")
    body = {"supplier_id": str(supplier.id), "items": [CEMENT]}
    stranger = await client.post(order_url(world), json=body, headers=bearer(other_contractor))
    assert stranger.status_code == 403
    assert stranger.json()["error"]["code"] == "not_project_member"
    for who in (world.client, world.supervisor):
        assert (await client.post(order_url(world), json=body, headers=bearer(who))).status_code == 403


async def test_signed_out_is_401(client: AsyncClient, world: World, supplier: Supplier) -> None:
    response = await client.post(order_url(world), json={"supplier_id": str(supplier.id), "items": [CEMENT]})
    assert response.status_code == 401


async def test_project_must_be_active(
    client: AsyncClient, db_session: AsyncSession, supplier: Supplier
) -> None:
    draft = await make_world(db_session, active=False)
    response = await place(client, draft, supplier, [CEMENT])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "project_not_active"


async def test_unknown_project_is_404(client: AsyncClient, world: World, supplier: Supplier) -> None:
    response = await client.post(
        f"/api/v1/projects/{uuid.uuid4()}/orders",
        json={"supplier_id": str(supplier.id), "items": [CEMENT]},
        headers=bearer(world.contractor),
    )
    assert response.status_code == 404


async def test_request_replays_with_the_same_idempotency_key(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    body = {"supplier_id": str(supplier.id), "items": [CEMENT]}
    headers = bearer(world.contractor) | {"Idempotency-Key": "order-1"}
    first = await client.post(order_url(world), json=body, headers=headers)
    second = await client.post(order_url(world), json=body, headers=headers)
    assert first.status_code == second.status_code == 201
    assert second.json() == first.json()
    orders = list(
        await db_session.scalars(select(MaterialOrder).where(MaterialOrder.project_id == world.project.id))
    )
    assert len(orders) == 1


# POST /orders/{id}/approve


async def requested_order(client: AsyncClient, world: World, supplier: Supplier) -> str:
    response = await place(client, world, supplier, [CEMENT])
    return str(response.json()["id"])


async def test_client_approves_an_order(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    order_id = await requested_order(client, world, supplier)
    response = await client.post(f"/api/v1/orders/{order_id}/approve", headers=bearer(world.client))
    assert response.status_code == 200
    out = response.json()
    assert out["status"] == "approved"
    assert out["approved_by"] == str(world.client.id)
    assert out["approved_at"] is not None
    entries = list(
        await db_session.scalars(
            select(AuditEntry).where(AuditEntry.object_id == uuid.UUID(order_id)).order_by(AuditEntry.at)
        )
    )
    assert [e.action for e in entries] == ["order.requested", "order.approved"]
    assert entries[1].before is not None and entries[1].before["status"] == "requested"


async def test_approving_twice_is_a_409(client: AsyncClient, world: World, supplier: Supplier) -> None:
    order_id = await requested_order(client, world, supplier)
    first = await client.post(f"/api/v1/orders/{order_id}/approve", headers=bearer(world.client))
    second = await client.post(f"/api/v1/orders/{order_id}/approve", headers=bearer(world.client))
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "invalid_order_transition"


async def test_approve_replays_with_the_same_idempotency_key(
    client: AsyncClient, world: World, supplier: Supplier
) -> None:
    order_id = await requested_order(client, world, supplier)
    headers = bearer(world.client) | {"Idempotency-Key": "approve-1"}
    first = await client.post(f"/api/v1/orders/{order_id}/approve", headers=headers)
    second = await client.post(f"/api/v1/orders/{order_id}/approve", headers=headers)
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()


async def test_only_the_projects_client_can_approve(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    order_id = await requested_order(client, world, supplier)
    other_client = await make_user(db_session, "client")
    other = await client.post(f"/api/v1/orders/{order_id}/approve", headers=bearer(other_client))
    assert other.status_code == 403
    assert other.json()["error"]["code"] == "not_project_member"
    for who in (world.contractor, world.supervisor, world.ops):
        response = await client.post(f"/api/v1/orders/{order_id}/approve", headers=bearer(who))
        assert response.status_code == 403
    still = await db_session.get(MaterialOrder, uuid.UUID(order_id))
    assert still is not None and still.status == "requested"


async def test_approving_an_unknown_order_is_404(client: AsyncClient, world: World) -> None:
    response = await client.post(f"/api/v1/orders/{uuid.uuid4()}/approve", headers=bearer(world.client))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "order_not_found"


async def test_signed_out_approve_is_401(client: AsyncClient, world: World, supplier: Supplier) -> None:
    order_id = await requested_order(client, world, supplier)
    assert (await client.post(f"/api/v1/orders/{order_id}/approve")).status_code == 401


async def test_a_cancelled_or_delivered_order_cannot_be_approved(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    for status in ("cancelled", "delivered", "paid"):
        order_id = await requested_order(client, world, supplier)
        order = await db_session.get(MaterialOrder, uuid.UUID(order_id))
        assert order is not None
        order.status = status
        await db_session.flush()
        response = await client.post(f"/api/v1/orders/{order_id}/approve", headers=bearer(world.client))
        assert response.status_code == 409
