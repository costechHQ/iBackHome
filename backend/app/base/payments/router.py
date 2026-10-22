"""HTTP endpoints for payments. Owner: Gabriel.

Routes are mounted under /api/v1 automatically; parse the request, check permissions,
call service.py, and return a schema. Keep business rules out of this file.

The webhook routes have no login (the providers call them); the signature is the only way in.
They check it on the raw body before parsing anything, then hand over to `webhooks.process()`.
"""

import json
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.base.payments import handlers, service, signatures, webhooks  # noqa: F401  (handlers: registers them)
from app.base.payments.paystack import (
    PaystackClient,
    PaystackDirectory,
    get_paystack_client,
    get_paystack_directory,
)
from app.base.payments.schemas import AccountIn, AccountNameOut, BankOut, PayoutRecipientOut, WebhookAck
from app.base.payments.service import EventResult, Provider
from app.base.users import service as users
from app.base.users.models import User
from app.core.db import SessionDep
from app.core.errors import AppError
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none

router = APIRouter(tags=["payments"])


def _parse(raw_body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError("webhook_invalid_payload", "The webhook body is not valid JSON.", 400) from exc
    if not isinstance(payload, dict):
        raise AppError("webhook_invalid_payload", "The webhook body must be a JSON object.", 400)
    return payload


async def _receive(
    request: Request,
    session: SessionDep,
    provider: Provider,
    verify: Callable[[bytes, str | None], None],
    header: str,
) -> WebhookAck:
    raw_body = await request.body()
    verify(raw_body, request.headers.get(header))
    result = await webhooks.process(session, provider, _parse(raw_body), request)
    await session.commit()
    return WebhookAck(received=True, duplicate=result is EventResult.DUPLICATE)


@router.post("/webhooks/stripe", response_model=WebhookAck)
async def stripe_webhook(request: Request, session: SessionDep) -> WebhookAck:
    """Stripe events, signed with STRIPE_WEBHOOK_SECRET (`Stripe-Signature`)."""
    return await _receive(request, session, "stripe", signatures.verify_stripe, signatures.STRIPE_HEADER)


@router.post("/webhooks/paystack", response_model=WebhookAck)
async def paystack_webhook(request: Request, session: SessionDep) -> WebhookAck:
    """Paystack events, signed with PAYSTACK_SECRET_KEY (`x-paystack-signature`)."""
    return await _receive(
        request, session, "paystack", signatures.verify_paystack, signatures.PAYSTACK_HEADER
    )


@router.post("/webhooks/escrow", response_model=WebhookAck)
async def escrow_webhook(request: Request, session: SessionDep) -> WebhookAck:
    """Escrow partner events, signed with ESCROW_WEBHOOK_SECRET (`X-Escrow-Signature`)."""
    return await _receive(request, session, "escrow", signatures.verify_escrow, signatures.ESCROW_HEADER)


# --- A contractor's own payout account (WEB-CONTRACTOR-002 step 2, gap MX-03) ------------------------
# "payout" in the path keeps every agent token off these routes (agents.service.FORBIDDEN_SEGMENTS).

DirectoryDep = Annotated[PaystackDirectory, Depends(get_paystack_directory)]
PaystackDep = Annotated[PaystackClient, Depends(get_paystack_client)]
ContractorDep = Annotated[User, Depends(users.require_role("contractor"))]


@router.get("/banks", response_model=list[BankOut])
async def banks(_user: users.CurrentUserDep, directory: DirectoryDep) -> list[BankOut]:
    """Nigerian banks a payout account can be in."""
    return [BankOut(code=b.code, name=b.name) for b in await service.list_banks(directory)]


@router.post("/me/payout/recipient/resolve", response_model=AccountNameOut)
async def resolve_account(
    payload: AccountIn, _user: ContractorDep, directory: DirectoryDep
) -> AccountNameOut:
    """Whose name the account is in, so the contractor can check it before saving. Saves nothing."""
    name = await service.resolve_account_name(payload.account_number, payload.bank_code, directory)
    return AccountNameOut(account_name=name)


@router.get("/me/payout/recipient", response_model=PayoutRecipientOut)
async def my_payout_recipient(session: SessionDep, user: ContractorDep) -> PayoutRecipientOut:
    """The account the contractor's releases are paid into (the number masked); 404 until one is saved."""
    recipient = await service.get_recipient_for(session, user_id=user.id)
    if recipient is None:
        raise AppError("no_payout_recipient", "No payout account saved yet.", 404)
    return PayoutRecipientOut.model_validate(recipient)


@router.put("/me/payout/recipient", response_model=PayoutRecipientOut)
async def save_payout_recipient(
    payload: AccountIn,
    request: Request,
    session: SessionDep,
    user: ContractorDep,
    directory: DirectoryDep,
    paystack: PaystackDep,
    key: IdempotencyKeyDep,
) -> Any:
    """Save (or change) the contractor's payout account. The name comes from the bank, not the request."""
    scope = f"PUT /me/payout/recipient {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    recipient = await service.save_own_payout_recipient(
        session,
        user.id,
        payload.account_number,
        payload.bank_code,
        directory=directory,
        client=paystack,
        request=request,
    )
    body = PayoutRecipientOut.model_validate(recipient).model_dump(mode="json")
    await remember(session, key, scope, 200, body)
    await session.commit()
    return body
