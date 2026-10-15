"""HTTP endpoints for material orders. Owner: Abigail."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.base.users.models import User
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.suppliers import service
from app.features.suppliers.schemas import OrderOut, OrderRequest

router = APIRouter(tags=["suppliers"])

ContractorUser = Annotated[User, Depends(users.require_role("contractor"))]
ClientUser = Annotated[User, Depends(users.require_role("client"))]


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
