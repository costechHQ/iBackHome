"""Business rules for suppliers: material orders. Owner: Abigail.

Other features call the functions in this file; they never query this feature's tables directly.
Every function takes the database session as its first argument.

An order moves requested -> approved (the project's client) -> delivered (the project's supervisor,
with photo evidence) -> paid (the system, once the supplier's payment is confirmed).
"""

import uuid
from collections import Counter
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.users.models import User
from app.core.errors import AppError
from app.features.evidence import service as evidence
from app.features.projects import service as projects
from app.features.projects.models import ProjectStatus
from app.features.suppliers import escrow_bridge
from app.features.suppliers.models import Delivery, MaterialOrder, OrderStatus, Supplier
from app.features.suppliers.schemas import DeliveryItem, OrderItem

# The only moves an order can make (anything else is a 409), and who makes them.
ALLOWED_TRANSITIONS: dict[tuple[str, str], str] = {
    (OrderStatus.REQUESTED.value, OrderStatus.APPROVED.value): "client",
    (OrderStatus.APPROVED.value, OrderStatus.DELIVERED.value): "supervisor",
    (OrderStatus.DELIVERED.value, OrderStatus.PAID.value): "system",
}


def order_total_minor(items: list[OrderItem]) -> int:
    """Sum of quantity x unit price in minor units, rounded half up once per line (integers only)."""
    return sum(
        int((i.quantity * i.unit_price_minor).quantize(Decimal(1), rounding=ROUND_HALF_UP)) for i in items
    )


def _items_json(items: list[OrderItem]) -> list[dict[str, object]]:
    return [
        {
            "item": i.item,
            "unit": i.unit,
            "quantity": format(i.quantity.normalize(), "f"),  # a string: no float ever touches it
            "unit_price_minor": i.unit_price_minor,
        }
        for i in items
    ]


async def request_order(
    session: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    supplier_id: uuid.UUID,
    items: list[OrderItem],
    request: Request | None = None,
) -> MaterialOrder:
    """The project's contractor asks for materials from a supplier. The project must be active."""
    project = await projects.require_project_member(session, user, project_id)
    if project.contractor_id != user.id:
        raise AppError("not_project_contractor", "Only the project's contractor can request materials.", 403)
    if project.status != ProjectStatus.ACTIVE.value:
        raise AppError("project_not_active", "Materials can only be ordered on an active project.", 409)
    if await session.get(Supplier, supplier_id) is None:
        raise AppError("supplier_not_found", "This supplier does not exist.", 404)

    total = order_total_minor(items)
    if total <= 0:
        raise AppError("invalid_order_total", "The order total must be more than zero.", 422)

    order = MaterialOrder(
        project_id=project_id,
        supplier_id=supplier_id,
        requested_by=user.id,
        items=_items_json(items),
        total_minor=total,
        currency=project.currency,
        status=OrderStatus.REQUESTED.value,
    )
    session.add(order)
    await session.flush()
    await session.refresh(order)
    await audit.record(
        session, user.id, "order.requested", "order", order.id, after=audit.snapshot(order), request=request
    )
    return order


async def get_order(session: AsyncSession, order_id: uuid.UUID, *, lock: bool = False) -> MaterialOrder:
    query = select(MaterialOrder).where(MaterialOrder.id == order_id)
    if lock:
        # Row lock: two requests can't both move the same order, and the row is re-read after it.
        query = query.with_for_update().execution_options(populate_existing=True)
    order = await session.scalar(query)
    if order is None:
        raise AppError("order_not_found", "Order not found.", 404)
    return order


async def approve_order(
    session: AsyncSession, user: User, order_id: uuid.UUID, request: Request | None = None
) -> MaterialOrder:
    """The project's client approves a requested order (requested -> approved)."""
    order = await get_order(session, order_id, lock=True)
    project = await projects.require_project_member(session, user, order.project_id)
    if project.client_id != user.id:
        raise AppError("not_project_client", "Only the project's client can approve an order.", 403)
    if ALLOWED_TRANSITIONS.get((order.status, OrderStatus.APPROVED.value)) != "client":
        raise AppError(
            "invalid_order_transition", f"An order that is {order.status} cannot be approved.", 409
        )

    before = audit.snapshot(order)
    order.status = OrderStatus.APPROVED.value
    order.approved_by = user.id
    order.approved_at = datetime.now(UTC)
    await session.flush()
    await session.refresh(order)
    await audit.record(
        session,
        user.id,
        "order.approved",
        "order",
        order.id,
        before=before,
        after=audit.snapshot(order),
        request=request,
    )
    return order


def _quantity_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _ordered_quantities(order: MaterialOrder) -> Counter[tuple[str, Decimal]]:
    return Counter((str(i["item"]), Decimal(str(i["quantity"]))) for i in order.items)


async def confirm_delivery(
    session: AsyncSession,
    user: User,
    order_id: uuid.UUID,
    quantities: list[DeliveryItem],
    evidence_ids: list[uuid.UUID],
    request: Request | None = None,
) -> tuple[Delivery, MaterialOrder]:
    """The project supervisor confirms an approved order arrived, then the supplier payment starts.

    - The quantities counted must match the order exactly (partial deliveries are not supported yet).
    - Every evidence id must be accepted evidence on this project taken by the supervisor.
    - approved -> delivered, audited, and escrow.pay_supplier() is called in the same transaction, so a
      delivery is never confirmed without the payment being started (or nothing is saved).
    """
    order = await get_order(session, order_id, lock=True)
    project = await projects.require_project_member(session, user, order.project_id)
    if project.supervisor_id != user.id:
        raise AppError("not_project_supervisor", "Only the project supervisor can confirm a delivery.", 403)
    if ALLOWED_TRANSITIONS.get((order.status, OrderStatus.DELIVERED.value)) != "supervisor":
        raise AppError(
            "invalid_order_transition", f"An order that is {order.status} cannot be delivered.", 409
        )

    counted = Counter((q.item, q.quantity) for q in quantities)
    if counted != _ordered_quantities(order):
        raise AppError(
            "quantity_mismatch",
            "The quantities must match the order exactly; partial deliveries are not supported yet.",
            422,
        )
    unique_ids = list(dict.fromkeys(evidence_ids))
    found = await evidence.accepted_supervisor_evidence_count(session, order.project_id, unique_ids)
    if found != len(unique_ids):
        raise AppError(
            "evidence_not_accepted",
            "Every photo must be accepted evidence on this project taken by its supervisor.",
            422,
        )

    before = audit.snapshot(order)
    delivery = Delivery(
        order_id=order.id,
        confirmed_by=user.id,
        quantities=[{"item": q.item, "quantity": _quantity_text(q.quantity)} for q in quantities],
        evidence_ids=[str(e) for e in unique_ids],
        confirmed_at=datetime.now(UTC),
    )
    session.add(delivery)
    order.status = OrderStatus.DELIVERED.value
    await session.flush()
    await session.refresh(delivery)
    await session.refresh(order)
    await audit.record(
        session,
        user.id,
        "order.delivered",
        "order",
        order.id,
        before=before,
        after={**audit.snapshot(order), "delivery_id": str(delivery.id)},
        request=request,
    )
    await escrow_bridge.pay_supplier(session, order.id)
    return delivery, order


async def mark_paid(session: AsyncSession, order_id: uuid.UUID) -> MaterialOrder:
    """The supplier payment was confirmed: delivered -> paid. For Gabriel's escrow and payments code."""
    order = await get_order(session, order_id, lock=True)
    if ALLOWED_TRANSITIONS.get((order.status, OrderStatus.PAID.value)) != "system":
        raise AppError("invalid_order_transition", f"An order that is {order.status} cannot be paid.", 409)
    before = audit.snapshot(order)
    order.status = OrderStatus.PAID.value
    await session.flush()
    await session.refresh(order)
    await audit.record(
        session, None, "order.paid", "order", order.id, before=before, after=audit.snapshot(order)
    )
    return order
