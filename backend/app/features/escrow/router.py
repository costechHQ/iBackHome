"""HTTP endpoints for escrow. Owner: Gabriel.

Routes parse the request, check the role, and call service.py, which checks project membership.
Importing `handlers` registers the Stripe funding webhook handler.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.base.payments.fx import FundingCurrency
from app.base.payments.stripe_checkout import CheckoutGateway, get_checkout_gateway
from app.base.users import service as users
from app.base.users.models import User
from app.core import pagination
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.escrow import handlers, service  # noqa: F401  (handlers: registers webhook handlers)
from app.features.escrow.schemas import (
    DisputeCreate,
    DisputeOut,
    DisputeResolutionOut,
    DisputeResolve,
    FundingCheckoutOut,
    FundingCreate,
    FundingQuoteOut,
    LedgerEntryOut,
    LedgerPage,
)

router = APIRouter(tags=["escrow"])

ClientUser = Annotated[User, Depends(users.require_role("client"))]
OpsUser = Annotated[User, Depends(users.require_role("ops"))]
GatewayDep = Annotated[CheckoutGateway, Depends(get_checkout_gateway)]


@router.get("/projects/{project_id}/funding/quote", response_model=FundingQuoteOut)
async def funding_quote(
    project_id: uuid.UUID,
    session: SessionDep,
    user: ClientUser,
    milestone_id: Annotated[uuid.UUID, Query()],
    currency: Annotated[FundingCurrency, Query(description="GBP, USD or EUR")],
) -> FundingQuoteOut:
    """Client: what funding this pending milestone would cost today (amount, fee, rate), before Stripe.

    Read-only: no checkout, no audit entry. Same checks and errors as POST /funding.
    """
    quote = await service.quote_milestone_funding(session, user, project_id, milestone_id, currency)
    return FundingQuoteOut(
        milestone_id=milestone_id,
        currency=quote.currency,
        amount_ngn_minor=quote.amount_ngn_minor,
        net_minor=quote.net_minor,
        fee_minor=quote.fee_minor,
        fee_bps=quote.fee_bps,
        total_minor=quote.total_minor,
        fx_rate=quote.fx_rate,
        fx_as_of=quote.fx_as_of,
    )


@router.post("/projects/{project_id}/funding", response_model=FundingCheckoutOut, status_code=201)
async def create_funding(
    project_id: uuid.UUID,
    data: FundingCreate,
    request: Request,
    session: SessionDep,
    user: ClientUser,
    key: IdempotencyKeyDep,
    gateway: GatewayDep,
) -> Any:
    """Client: get a Stripe Checkout link to pay for one pending milestone (its naira amount + fee).

    Nothing is recorded as paid until Stripe confirms by webhook. Send an `Idempotency-Key`:
    a retry with the same key returns the same checkout link (also passed on to Stripe).
    """
    scope = f"POST /projects/{project_id}/funding by {user.id}"
    saved: JSONResponse | None = await replay_or_none(session, key, scope)
    if saved is not None:
        return saved
    checkout = await service.create_funding_checkout(
        session,
        user,
        project_id,
        data.milestone_id,
        data.currency,
        gateway=gateway,
        idempotency_key=key,
        request=request,
    )
    quote = checkout.quote
    body = FundingCheckoutOut(
        project_id=checkout.project_id,
        milestone_id=checkout.milestone_id,
        checkout_session_id=checkout.checkout_session_id,
        checkout_url=checkout.checkout_url,
        currency=quote.currency,
        amount_ngn_minor=quote.amount_ngn_minor,
        net_minor=quote.net_minor,
        fee_minor=quote.fee_minor,
        fee_bps=quote.fee_bps,
        total_minor=quote.total_minor,
        fx_rate=quote.fx_rate,
        fx_as_of=quote.fx_as_of,
    ).model_dump(mode="json")
    await remember(session, key, scope, 201, body)
    await session.commit()
    return body


@router.get("/projects/{project_id}/ledger", response_model=LedgerPage)
async def project_ledger(
    project_id: uuid.UUID,
    session: SessionDep,
    user: users.CurrentUserDep,
    since: Annotated[datetime | None, Query(description="Inclusive, ISO 8601 date or time")] = None,
    until: Annotated[datetime | None, Query(description="Exclusive, ISO 8601")] = None,
    cursor: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=pagination.DEFAULT_LIMIT, ge=1, le=pagination.MAX_LIMIT),
) -> LedgerPage:
    """The project's client or ops: funding, releases and payouts, newest first (`?cursor=&limit=`)."""
    entries, next_cursor = await service.project_ledger(
        session, user, project_id, since=since, until=until, cursor=cursor, limit=limit
    )
    return LedgerPage(items=[LedgerEntryOut.model_validate(e) for e in entries], next_cursor=next_cursor)


@router.post("/milestones/{milestone_id}/disputes", response_model=DisputeOut, status_code=201)
async def raise_dispute(
    milestone_id: uuid.UUID,
    data: DisputeCreate,
    request: Request,
    session: SessionDep,
    user: users.CurrentUserDep,
    key: IdempotencyKeyDep,
) -> Any:
    """Client: dispute a verified milestone. It becomes `disputed`; nothing is released until resolved."""
    scope = f"POST /milestones/{milestone_id}/disputes by {user.id}"
    saved: JSONResponse | None = await replay_or_none(session, key, scope)
    if saved is not None:
        return saved
    dispute = await service.raise_dispute(session, user, milestone_id, data.reason, request)
    body = DisputeOut.model_validate(dispute).model_dump(mode="json")
    await remember(session, key, scope, 201, body)
    await session.commit()
    return body


@router.post("/disputes/{dispute_id}/resolve", response_model=DisputeResolutionOut)
async def resolve_dispute(
    dispute_id: uuid.UUID,
    data: DisputeResolve,
    request: Request,
    session: SessionDep,
    user: OpsUser,
    key: IdempotencyKeyDep,
) -> Any:
    """Ops: resolve a dispute. Needs two different ops users choosing the same outcome; the first
    call records a proposal (`resolved: false`), the second resolves it."""
    scope = f"POST /disputes/{dispute_id}/resolve by {user.id}"
    saved: JSONResponse | None = await replay_or_none(session, key, scope)
    if saved is not None:
        return saved
    result = await service.resolve_dispute(session, user, dispute_id, data.outcome, data.notes, request)
    await session.flush()
    await session.refresh(result.dispute)
    body = DisputeResolutionOut(
        dispute=DisputeOut.model_validate(result.dispute),
        resolved=result.resolved,
        release_id=result.release_id,
    ).model_dump(mode="json")
    await remember(session, key, scope, 200, body)
    await session.commit()
    return body
