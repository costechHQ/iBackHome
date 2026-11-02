"""HTTP endpoints for material orders. Owner: Abigail."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.base.users.models import User
from app.core import pagination
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.suppliers import service
from app.features.suppliers.models import Delivery, MaterialOrder, Supplier
from app.features.suppliers.schemas import (
    DeliveryIn,
    DeliveryOut,
    OrderDetail,
    OrderOut,
    OrderPage,
    OrderRequest,
    SupplierRef,
)

router = APIRouter(tags=["suppliers"])

ContractorUser = Annotated[User, Depends(users.require_role("contractor"))]
ClientUser = Annotated[User, Depends(users.require_role("client"))]
SupervisorUser = Annotated[User, Depends(users.require_role("supervisor"))]


def _detail(
    order: MaterialOrder, suppliers: dict[uuid.UUID, Supplier], deliveries: dict[uuid.UUID, Delivery]
) -> OrderDetail:
    supplier = suppliers[order.supplier_id]
    delivery = deliveries.get(order.id)
    return OrderDetail(
        **OrderOut.model_validate(order).model_dump(),
        supplier=SupplierRef(id=supplier.id, name=supplier.name),
        delivery=DeliveryOut.model_validate(delivery) if delivery else None,
    )


@router.get("/projects/{project_id}/orders", response_model=OrderPage)
async def list_orders(
    project_id: uuid.UUID,
    session: SessionDep,
    user: users.CurrentUserDep,
    cursor: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=pagination.DEFAULT_LIMIT, ge=1, le=pagination.MAX_LIMIT),
) -> OrderPage:
    """A project's material orders, newest first, with each supplier's name and its delivery count if any.

    For the project's client, contractor, assigned supervisor, and ops.
    """
    orders, next_cursor = await service.list_orders(session, user, project_id, cursor=cursor, limit=limit)
    suppliers, deliveries = await service.suppliers_and_deliveries(session, orders)
    return OrderPage(items=[_detail(o, suppliers, deliveries) for o in orders], next_cursor=next_cursor)


@router.get("/orders/{order_id}", response_model=OrderDetail)
async def get_order(order_id: uuid.UUID, session: SessionDep, user: users.CurrentUserDep) -> OrderDetail:
    """One order with its supplier's name and its delivery count if any (same people as the list)."""
    order = await service.read_order(session, user, order_id)
    suppliers, deliveries = await service.suppliers_and_deliveries(session, [order])
    return _detail(order, suppliers, deliveries)


@router.post("/projects/{project_id}/orders", status_code=201, response_model=OrderOut)
async def request_order(
    project_id: uuid.UUID,
    body: OrderRequest,
    request: Request,
    session: SessionDep,
    user: ContractorUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Contractor: request materials from a supplier. The total is worked out by the server."""
    scope = f"POST /projects/{project_id}/orders {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    order = await service.request_order(session, user, project_id, body.supplier_id, body.items, request)
    out = OrderOut.model_validate(order).model_dump(mode="json")
    await remember(session, key, scope, 201, out)
    await session.commit()
    return JSONResponse(status_code=201, content=out)


@router.post("/orders/{order_id}/approve", response_model=OrderOut)
async def approve_order(
    order_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    user: ClientUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Client: approve a requested order."""
    scope = f"POST /orders/{order_id}/approve {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    order = await service.approve_order(session, user, order_id, request)
    out = OrderOut.model_validate(order).model_dump(mode="json")
    await remember(session, key, scope, 200, out)
    await session.commit()
    return JSONResponse(status_code=200, content=out)


@router.post("/orders/{order_id}/delivery", status_code=201, response_model=DeliveryOut)
async def confirm_delivery(
    order_id: uuid.UUID,
    body: DeliveryIn,
    request: Request,
    session: SessionDep,
    user: SupervisorUser,
    key: IdempotencyKeyDep,
) -> JSONResponse:
    """Supervisor: confirm an approved order arrived, with the quantities counted and photo evidence.

    This starts the supplier payment, so it only succeeds when the payment can be started.
    """
    scope = f"POST /orders/{order_id}/delivery {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    delivery, _ = await service.confirm_delivery(
        session, user, order_id, body.quantities, body.evidence_ids, request
    )
    out = DeliveryOut.model_validate(delivery).model_dump(mode="json")
    await remember(session, key, scope, 201, out)
    await session.commit()
    return JSONResponse(status_code=201, content=out)
