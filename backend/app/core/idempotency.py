"""Idempotency-Key support for write endpoints.

Clients (web, Flutter sync queue) send an `Idempotency-Key` header on every write.
If the same key arrives again for the same endpoint, we return the stored response
instead of doing the work twice. Use it like this in a router:

    from app.core.idempotency import IdempotencyKeyDep, replay_or_none, remember

    @router.post("/milestones/{milestone_id}/claim")
    async def claim(milestone_id: UUID, session: SessionDep, key: IdempotencyKeyDep):
        scope = f"POST /milestones/{milestone_id}/claim"
        if (saved := await replay_or_none(session, key, scope)) is not None:
            return saved
        result = await service.claim(session, milestone_id)
        body = MilestoneOut.model_validate(result).model_dump(mode="json")
        await remember(session, key, scope, 200, body)
        await session.commit()
        return body
"""

from typing import Annotated, Any

from fastapi import Header
from fastapi.responses import JSONResponse
from sqlalchemy import JSON, Integer, String, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class IdempotencyRecord(TimestampedBase):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("key", "scope", name="uq_idempotency_keys_key_scope"),)

    key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


IdempotencyKeyDep = Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)]


async def replay_or_none(session: AsyncSession, key: str | None, scope: str) -> JSONResponse | None:
    """Return the stored response if this key was already used for this scope."""
    if not key:
        return None
    record = await session.scalar(
        select(IdempotencyRecord).where(IdempotencyRecord.key == key, IdempotencyRecord.scope == scope)
    )
    if record is None:
        return None
    return JSONResponse(status_code=record.status_code, content=record.response)


async def remember(
    session: AsyncSession,
    key: str | None,
    scope: str,
    status_code: int,
    body: dict[str, Any],
) -> None:
    """Store the response in the same transaction as the work (caller commits)."""
    if not key:
        return
    session.add(IdempotencyRecord(key=key, scope=scope, status_code=status_code, response=body))
