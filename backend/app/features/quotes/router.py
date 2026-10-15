"""HTTP endpoints for the quote checker. Owner: Gabriel."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.base.users import service as users
from app.base.users.models import User
from app.core.db import SessionDep
from app.core.errors import AppError
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none
from app.features.agents import llm
from app.features.quotes import service
from app.features.quotes.schemas import QuoteCheckIn, QuoteCheckOut

router = APIRouter(tags=["quotes"])

QuoteUser = Annotated[User, Depends(users.require_role("client", "contractor", "ops"))]


def get_quote_llm() -> llm.LLMClient | None:
    """The model client (None: the configured one). Tests override this dependency."""
    return None


LLMDep = Annotated[llm.LLMClient | None, Depends(get_quote_llm)]


@router.post("/quotes/check", response_model=QuoteCheckOut)
async def check_quote(
    data: QuoteCheckIn, session: SessionDep, user: QuoteUser, key: IdempotencyKeyDep, client: LLMDep
) -> Any:
    """Client, contractor or ops: flag the lines of a quote that are more than 15% above the price index.

    Send the PDF as base64 (`pdf_base64`) or the quote as `text`. The model only reads the lines;
    the comparison is plain code, and every price shown comes from the quote or the index.
    """
    scope = f"POST /quotes/check by {user.id}"
    saved: JSONResponse | None = await replay_or_none(session, key, scope)
    if saved is not None:
        return saved
    pdf = service.decode_pdf(data.pdf_base64) if data.pdf_base64 is not None else None
    try:
        result = await service.check_quote(session, user, pdf=pdf, text=data.text, client=client)
    except AppError as exc:
        if exc.code == "quote_parse_failed":
            await session.commit()  # keep the failed agent run for the record
        raise
    body = result.model_dump(mode="json")
    await remember(session, key, scope, 200, body)
    await session.commit()
    return body
