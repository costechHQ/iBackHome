"""Business rules for escrow. Owner: Gabriel.

Other features call the functions in this file; they never query this feature's tables directly.
Every function takes the database session as its first argument.

What other features call:

    from app.features.escrow import service as escrow

    release = await escrow.request_release(session, milestone.id, actor)   # Lilian, on approve
    account = await escrow.get_or_create_account(session, project_id)
"""

import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.core.errors import AppError
from app.features.escrow.models import EscrowAccount
from app.features.escrow.settings import get_escrow_settings

# The spec's escrow release states: requested -> submitted -> released, or failed.
ReleaseStatus = Literal["requested", "submitted", "released", "failed"]

# Returned by the day-2 stub only. A real release id is never the nil UUID.
PLACEHOLDER_RELEASE_ID = uuid.UUID(int=0)


@dataclass(frozen=True)
class ReleaseRequest:
    release_id: uuid.UUID  # the escrow_releases row; use it to look the release up later
    milestone_id: uuid.UUID
    status: ReleaseStatus


async def request_release(session: AsyncSession, milestone_id: uuid.UUID, actor: User) -> ReleaseRequest:
    """Ask the escrow partner to release a milestone's money to the contractor.

    STUB (day 2): returns a fixed placeholder (`release_id=PLACEHOLDER_RELEASE_ID`,
    `status="requested"`) and does nothing else: no database access, no provider call.
    The signature is final, so callers can wire it in now.

    Real behaviour (day 4), all inside the caller's transaction; this function never commits:
    - Refuses with AppError 409 if the milestone is not `approved` (or a dispute was resolved
      for release), if a dispute on it is open, or if a release was already requested for it.
      Calling it again for the same milestone returns the existing release instead of a second one.
    - Creates an `escrow_releases` row (`requested`), calls `EscrowProvider.release(...)` with the
      release id as the idempotency `ref`, and moves the row to `submitted`.
    - Writes the ledger entries (debit `contractor_payable`, credit `escrow:{project}`) and an
      audit entry with `actor` as the actor.
    - Does NOT mark the milestone `released`: that happens when the partner's confirmation webhook
      arrives (spec: approved -> released is a system transition).
    """
    return ReleaseRequest(release_id=PLACEHOLDER_RELEASE_ID, milestone_id=milestone_id, status="requested")


async def get_or_create_account(
    session: AsyncSession, project_id: uuid.UUID, currency: str = "NGN", *, lock: bool = False
) -> EscrowAccount:
    """The project's escrow account, created on first use with the configured provider.

    Safe to call twice or concurrently: the insert is ON CONFLICT DO NOTHING on the unique
    project_id, then the row is read (locked FOR UPDATE when `lock`, before changing its balance).
    Does not commit.
    """
    await session.execute(
        insert(EscrowAccount)
        .values(
            id=uuid.uuid4(),
            project_id=project_id,
            provider=get_escrow_settings().escrow_provider,
            currency=currency,
            balance_minor=0,
        )
        .on_conflict_do_nothing(index_elements=["project_id"])
    )
    query = select(EscrowAccount).where(EscrowAccount.project_id == project_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    account = await session.scalar(query)
    if account is None:  # pragma: no cover - the insert above guarantees a row
        raise RuntimeError(f"escrow account for project {project_id} vanished")
    if account.currency != currency:
        raise AppError(
            "escrow_currency_mismatch",
            f"This project's escrow account is in {account.currency}, not {currency}.",
            409,
        )
    return account
