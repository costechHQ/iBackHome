"""HTTP endpoints for subscriptions. Owner: Christopher.

Routes parse the request, check the role, and call service.py. Importing `handlers` registers the
Stripe webhook handlers.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.base.payments.stripe_billing import BillingGateway, get_billing_gateway
from app.base.users import service as users
from app.base.users.models import User
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.subscriptions import handlers, plans, service  # noqa: F401  (handlers: registers webhook handlers)
from app.features.subscriptions.schemas import (
    PlanOut,
    SubscriptionCheckoutOut,
    SubscriptionCreate,
    SubscriptionOut,
)

router = APIRouter(tags=["subscriptions"])

ClientUser = Annotated[User, Depends(users.require_role("client"))]
GatewayDep = Annotated[BillingGateway, Depends(get_billing_gateway)]


@router.get("/subscription/plans", response_model=list[PlanOut])
async def list_plans() -> Any:
    """Public: the three plans with monthly price, visits per month and the price of each billing period."""
    return plans.list_plans()


@router.post("/projects/{project_id}/subscription", response_model=SubscriptionCheckoutOut, status_code=201)
async def start_subscription(
    project_id: uuid.UUID,
    data: SubscriptionCreate,
    request: Request,
    session: SessionDep,
    user: ClientUser,
    key: IdempotencyKeyDep,
    gateway: GatewayDep,
) -> Any:
    """Client: get a Stripe Checkout link for the supervision fee on the chosen plan and billing period (USD).

    Nothing counts until Stripe confirms by webhook. Send an `Idempotency-Key`: a retry with the
    same key returns the same link.
    """
    scope = f"POST /projects/{project_id}/subscription by {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    subscription, session_id, url = await service.create_checkout(
        session,
        user,
        project_id,
        data.plan,
        data.billing_period,
        gateway=gateway,
        idempotency_key=key,
        request=request,
    )
    body = SubscriptionCheckoutOut(
        project_id=project_id,
        checkout_session_id=session_id,
        checkout_url=url,
        plan=subscription.plan,  # type: ignore[arg-type]
        billing_period=subscription.billing_period,  # type: ignore[arg-type]
        visits_per_month=plans.visits_for(subscription.plan),
        currency=subscription.currency,
        amount_minor=subscription.amount_minor,
    ).model_dump(mode="json")
    await remember(session, key, scope, 201, body)
    await session.commit()
    return body


@router.get("/projects/{project_id}/subscription", response_model=SubscriptionOut)
async def get_subscription(project_id: uuid.UUID, session: SessionDep, user: users.CurrentUserDep) -> Any:
    """Project members and ops: status, price and renewal date; 404 until one is started."""
    return await service.get_subscription(session, user, project_id)


@router.post("/projects/{project_id}/subscription/cancel", response_model=SubscriptionOut)
async def cancel_subscription(
    project_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    user: ClientUser,
    gateway: GatewayDep,
) -> Any:
    """Client: stop renewing at the end of the paid month. The project keeps running until then."""
    subscription = await service.cancel(session, user, project_id, gateway=gateway, request=request)
    out = SubscriptionOut.model_validate(subscription)
    await session.commit()
    return out
