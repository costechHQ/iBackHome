"""GET /projects/{id}/orders and GET /orders/{id}: who may read orders, and what they see."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.evidence.tests.conftest import World, bearer, make_user, make_world
from app.features.suppliers.models import Delivery, MaterialOrder, Supplier

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
CEMENT = {"item": "Cement, 50 kg bag", "unit": "bag", "quantity": "10", "unit_price_minor": 100_000}
NO_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    return await make_world(db_session)


@pytest.fixture
async def supplier(db_session: AsyncSession) -> Supplier:
    row = Supplier(
        name="Enugu Building Supplies",
        verified=True,
        address="1 Market Road",
        paystack_recipient_code="RCP_secret",
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def add_order(
    session: AsyncSession, world: World, supplier: Supplier, *, minutes: int = 0, status: str = "requested"
) -> MaterialOrder:
    order = MaterialOrder(
        project_id=world.project.id,
        supplier_id=supplier.id,
        requested_by=world.contractor.id,
        items=[CEMENT],
        total_minor=1_000_000,
        currency="NGN",
        status=status,
    )
    order.created_at = T0 + timedelta(minutes=minutes)
    session.add(order)
    await session.flush()
    return order


async def add_delivery(session: AsyncSession, world: World, order: MaterialOrder) -> Delivery:
    delivery = Delivery(
        order_id=order.id,
        confirmed_by=world.supervisor.id,
        quantities=[{"item": CEMENT["item"], "quantity": "10"}],
        evidence_ids=[str(uuid.uuid4())],
        confirmed_at=T0 + timedelta(days=1),
    )
    session.add(delivery)
    await session.flush()
    return delivery


def url(world: World) -> str:
    return f"/api/v1/projects/{world.project.id}/orders"


# --- the project's list ------------------------------------------------------------------------


async def test_every_member_reads_the_list_newest_first_with_the_suppliers_name(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    older = await add_order(db_session, world, supplier, minutes=0)
    newer = await add_order(db_session, world, supplier, minutes=5, status="approved")
    for viewer in (world.client, world.contractor, world.supervisor, world.ops):
        response = await client.get(url(world), headers=bearer(viewer))
        assert response.status_code == 200, response.text
        body = response.json()
        assert [o["id"] for o in body["items"]] == [str(newer.id), str(older.id)]
        first = body["items"][0]
        assert first["supplier"] == {"id": str(supplier.id), "name": "Enugu Building Supplies"}
        assert first["status"] == "approved"
        assert first["total_minor"] == 1_000_000
        assert first["currency"] == "NGN"
        assert first["items"] == [CEMENT]
        assert first["delivery"] is None
        assert body["next_cursor"] is None


async def test_the_supplier_is_only_an_id_and_a_name(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    await add_order(db_session, world, supplier)
    body = (await client.get(url(world), headers=bearer(world.client))).json()
    assert set(body["items"][0]["supplier"]) == {"id", "name"}
    assert "RCP_secret" not in str(body)
    assert "Market Road" not in str(body)


async def test_a_delivered_order_carries_its_delivery_count(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    order = await add_order(db_session, world, supplier, status="delivered")
    delivery = await add_delivery(db_session, world, order)
    item = (await client.get(url(world), headers=bearer(world.contractor))).json()["items"][0]
    assert item["delivery"]["id"] == str(delivery.id)
    assert item["delivery"]["quantities"] == [{"item": CEMENT["item"], "quantity": "10"}]
    assert item["delivery"]["evidence_ids"] == delivery.evidence_ids
    assert item["delivery"]["confirmed_by"] == str(world.supervisor.id)
    assert item["delivery"]["confirmed_at"] is not None


async def test_only_this_projects_orders_are_listed(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    mine = await add_order(db_session, world, supplier)
    other_world = await make_world(db_session)
    await add_order(db_session, other_world, supplier)
    items = (await client.get(url(world), headers=bearer(world.client))).json()["items"]
    assert [o["id"] for o in items] == [str(mine.id)]


async def test_a_project_with_no_orders_is_an_empty_list(client: AsyncClient, world: World) -> None:
    body = (await client.get(url(world), headers=bearer(world.client))).json()
    assert body == {"items": [], "next_cursor": None}


async def test_pages_follow_the_cursor_without_repeats(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    orders = [await add_order(db_session, world, supplier, minutes=m) for m in range(5)]
    seen: list[str] = []
    cursor: str | None = None
    for _ in range(5):
        extra = f"&cursor={cursor}" if cursor else ""
        body = (await client.get(f"{url(world)}?limit=2{extra}", headers=bearer(world.client))).json()
        seen += [o["id"] for o in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == [str(o.id) for o in reversed(orders)]


async def test_a_bad_cursor_is_422(client: AsyncClient, world: World) -> None:
    response = await client.get(f"{url(world)}?cursor=nonsense", headers=bearer(world.client))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_cursor"


@pytest.mark.parametrize("role", ["client", "contractor", "supervisor", "supplier"])
async def test_someone_not_on_the_project_is_refused(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier, role: str
) -> None:
    await add_order(db_session, world, supplier)
    stranger = await make_user(db_session, role)
    response = await client.get(url(world), headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"
    assert "Enugu Building Supplies" not in response.text


async def test_an_unknown_project_is_404(client: AsyncClient, world: World) -> None:
    response = await client.get(f"/api/v1/projects/{NO_ID}/orders", headers=bearer(world.client))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "project_not_found"


async def test_signed_out_is_401(client: AsyncClient, world: World) -> None:
    assert (await client.get(url(world))).status_code == 401
    assert (await client.get(f"/api/v1/orders/{NO_ID}")).status_code == 401


# --- one order ---------------------------------------------------------------------------------


async def test_a_member_reads_one_order_with_its_delivery(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    order = await add_order(db_session, world, supplier, status="delivered")
    await add_delivery(db_session, world, order)
    for viewer in (world.client, world.contractor, world.supervisor, world.ops):
        response = await client.get(f"/api/v1/orders/{order.id}", headers=bearer(viewer))
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        assert body["id"] == str(order.id)
        assert body["supplier"]["name"] == "Enugu Building Supplies"
        assert body["delivery"]["confirmed_by"] == str(world.supervisor.id)


async def test_one_order_matches_what_the_list_shows(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    order = await add_order(db_session, world, supplier)
    listed = (await client.get(url(world), headers=bearer(world.client))).json()["items"][0]
    single = (await client.get(f"/api/v1/orders/{order.id}", headers=bearer(world.client))).json()
    assert single == listed


async def test_someone_not_on_the_project_cannot_read_the_order(
    client: AsyncClient, db_session: AsyncSession, world: World, supplier: Supplier
) -> None:
    order = await add_order(db_session, world, supplier)
    stranger = await make_user(db_session, "contractor")
    response = await client.get(f"/api/v1/orders/{order.id}", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"


async def test_an_unknown_order_is_404(client: AsyncClient, world: World) -> None:
    response = await client.get(f"/api/v1/orders/{NO_ID}", headers=bearer(world.client))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "order_not_found"
