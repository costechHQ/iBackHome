"""HTTP endpoints for payments. Owner: Gabriel.

Routes are mounted under /api/v1 automatically; parse the request, check permissions,
call service.py, and return a schema. Keep business rules out of this file.

The webhook routes have no login (the providers call them); the signature is the only way in.
They check it on the raw body before parsing anything, then hand over to `webhooks.process()`.
"""

import json
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request

from app.base.payments import handlers, signatures, webhooks  # noqa: F401  (handlers: registers them)
from app.base.payments.schemas import WebhookAck
from app.base.payments.service import EventResult, Provider
from app.core.db import SessionDep
from app.core.errors import AppError

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
