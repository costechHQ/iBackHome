"""HTTP endpoint for the website assistant (ADR 0006). Owner: Christopher.

POST /api/v1/assistant/chat is public (no login), so it is rate limited per IP address and for the whole day,
and it stays off until ASSISTANT_ENABLED=true. It reads nothing and writes nothing: no database, no user data,
and nothing a visitor typed is stored. It changes no state, so it takes no Idempotency-Key.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.errors import AppError
from app.features.assistant import service
from app.features.assistant.ratelimit import RateLimiter, get_limiter
from app.features.assistant.schemas import AssistantChatIn, AssistantChatOut, AssistantRelatedQuestion
from app.features.assistant.settings import get_assistant_settings

log = logging.getLogger(__name__)

router = APIRouter(tags=["assistant"])

Limiter = Annotated[RateLimiter, Depends(get_limiter)]


@router.post("/assistant/chat", response_model=AssistantChatOut)
async def chat(payload: AssistantChatIn, request: Request, limiter: Limiter) -> AssistantChatOut:
    """Answer one question from the vetted answers, or hand off to a person."""
    settings = get_assistant_settings()
    if not settings.assistant_enabled:
        raise AppError("assistant_unavailable", "The assistant isn't available right now.", 503)
    ip = request.client.host if request.client else "unknown"
    wait = await limiter.hit_ip(
        ip, settings.assistant_limit_per_ip, settings.assistant_limit_window_minutes * 60
    )
    if wait is not None:
        raise HTTPException(
            429,
            "Too many questions from this connection. Try again later.",
            headers={"Retry-After": str(wait)},
        )
    if not await limiter.hit_day(settings.assistant_daily_cap):
        raise AppError("assistant_busy", "The assistant is busy today. Please contact us instead.", 503)
    reply = service.answer(payload.message)
    # Counts only: never the question, never the address. (The structured log carries the request id.)
    log.info(
        "assistant answered",
        extra={"source": reply.source, "entry": reply.entry_id, "handoff": reply.handoff},
    )
    return AssistantChatOut(
        answer=reply.text,
        related=[AssistantRelatedQuestion(question=q) for q in reply.related],
        handoff=reply.handoff,
        source="none" if reply.source == "none" else "faq",
    )
