"""Test helpers for releases: held milestones, approvals, payout recipients, a fake Paystack, and
signed Paystack / escrow webhooks. Built on factories.py (the funding helpers)."""

import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import accounts, credit, debit, post_transaction
from app.base.payments.models import LedgerEntry, Payout, PayoutRecipient
from app.base.payments.paystack import TransferResult
from app.base.payments.tests.webhook_helpers import body, escrow_headers, paystack_headers
from app.core.errors import AppError
from app.features.escrow import service as escrow
from app.features.escrow.models import EscrowHold
from app.features.escrow.tests.factories import Funded, simulated_escrow
from app.features.milestones import service as milestones
from app.features.milestones.models import Milestone, MilestoneStatus
from app.features.milestones.transitions import ActorRole

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def session_factory(session: AsyncSession) -> SessionFactory:
    """A task session factory that hands out the test's own rolled-back session."""

    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncSession]:
        yield session

    return factory


async def hold_milestone(session: AsyncSession, project_id: uuid.UUID, milestone: Milestone) -> EscrowHold:
    """What a paid Stripe checkout leaves behind (see fund_from_checkout): the partner holds the
    naira, the ledger shows it in escrow, the milestone is funded."""
    hold = await simulated_escrow().hold(
        project_id, milestone.amount_minor, "NGN", ref=f"stripe_checkout:cs_test_{uuid.uuid4().hex}"
    )
    row = EscrowHold(
        project_id=project_id,
        milestone_id=milestone.id,
        ref=hold.ref,
        provider_ref=hold.provider_ref,
        amount_minor=milestone.amount_minor,
        currency="NGN",
        status="held",
    )
    session.add(row)
    rate = Decimal("2000")
    await post_transaction(
        session,
        [
            debit(accounts.escrow(project_id, "NGN"), milestone.amount_minor, "NGN", rate),
            credit(accounts.fx_conversion("NGN"), milestone.amount_minor, "NGN", rate),
        ],
        ref_type="payment_event",
        ref_id=uuid.uuid4(),
    )
    account = await escrow.get_or_create_account(session, project_id, "NGN", lock=True)
    account.balance_minor += milestone.amount_minor
    await milestones.mark_funded(session, milestone.id)
    await session.flush()
    return row


async def approve_milestone(session: AsyncSession, funded: Funded, milestone: Milestone) -> None:
    """funded -> claimed -> verified -> approved, as the contractor, supervisor and client would."""
    steps = (
        (MilestoneStatus.CLAIMED, ActorRole.CONTRACTOR, funded.contractor.id),
        (MilestoneStatus.VERIFIED, ActorRole.SUPERVISOR, None),
        (MilestoneStatus.APPROVED, ActorRole.CLIENT, funded.client.id),
    )
    for status, role, actor_id in steps:
        await milestones.transition(session, milestone.id, status, role, actor_id)


async def add_recipient(
    session: AsyncSession, *, user_id: uuid.UUID | None = None, supplier_id: uuid.UUID | None = None
) -> PayoutRecipient:
    """A registered Paystack recipient (normally made by register_payout_recipient)."""
    recipient = PayoutRecipient(
        user_id=user_id,
        supplier_id=supplier_id,
        provider="paystack",
        recipient_code=f"RCP_{uuid.uuid4().hex[:12]}",
        bank_code="058",
        bank_name="GTBank",
        account_name="Chidi Okeke",
        account_number_masked="******6789",
        currency="NGN",
    )
    session.add(recipient)
    await session.flush()
    return recipient


@dataclass
class FakePaystack:
    """Stands in for Paystack transfers. Queue answers: a TransferResult, or an AppError to raise."""

    initiate_answers: list[TransferResult | AppError] = field(default_factory=list)
    verify_answers: list[TransferResult | None] = field(default_factory=list)
    initiated: list[str] = field(default_factory=list)
    verified: list[str] = field(default_factory=list)

    async def create_transfer_recipient(self, account_name: str, account_number: str, bank_code: str) -> Any:
        raise NotImplementedError

    async def initiate_transfer(
        self, amount_minor: int, recipient_code: str, reference: str, reason: str
    ) -> TransferResult:
        self.initiated.append(reference)
        answer: TransferResult | AppError = (
            self.initiate_answers.pop(0)
            if self.initiate_answers
            else TransferResult(reference, f"TRF_{uuid.uuid4().hex[:10]}", "pending")
        )
        if isinstance(answer, AppError):
            raise answer
        return answer

    async def verify_transfer(self, reference: str) -> TransferResult | None:
        self.verified.append(reference)
        return self.verify_answers.pop(0) if self.verify_answers else None


@dataclass
class Queued:
    """What would have gone to Celery after each commit: release ids and payout ids, in order."""

    releases: list[uuid.UUID] = field(default_factory=list)
    payouts: list[uuid.UUID] = field(default_factory=list)


def transfer_event(event: str, payout: Payout, **data: Any) -> dict[str, Any]:
    """A Paystack transfer.* webhook body for one of our payouts."""
    return {
        "event": event,
        "data": {
            "id": int(payout.id.int % 10**9),
            "reference": payout.reference,
            "transfer_code": payout.provider_transfer_code,
            "amount": payout.amount_minor,
            "currency": "NGN",
            **data,
        },
    }


def release_event(event_type: str, release_id: uuid.UUID, **data: Any) -> dict[str, Any]:
    """The escrow partner's release.* webhook (our scheme)."""
    return {"id": f"esc_{uuid.uuid4().hex}", "type": event_type, "data": {"ref": str(release_id), **data}}


async def send_paystack(client: AsyncClient, event: dict[str, Any]) -> Response:
    raw = body(event)
    return await client.post("/api/v1/webhooks/paystack", content=raw, headers=paystack_headers(raw))


async def send_escrow(client: AsyncClient, event: dict[str, Any]) -> Response:
    raw = body(event)
    return await client.post("/api/v1/webhooks/escrow", content=raw, headers=escrow_headers(raw))


async def all_entries(session: AsyncSession) -> list[LedgerEntry]:
    return list(await session.scalars(select(LedgerEntry).order_by(LedgerEntry.created_at, LedgerEntry.id)))


async def entries_of_release(session: AsyncSession, release_id: uuid.UUID) -> list[LedgerEntry]:
    result = await session.scalars(
        select(LedgerEntry)
        .where(LedgerEntry.ref_type == "escrow_release", LedgerEntry.ref_id == release_id)
        .order_by(LedgerEntry.created_at, LedgerEntry.id)
    )
    return list(result)


def unbalanced(entries: list[LedgerEntry]) -> dict[uuid.UUID, int]:
    """Transactions whose debits and credits differ (must always be empty)."""
    totals: dict[uuid.UUID, int] = {}
    for e in entries:
        signed = e.amount_minor if e.direction == "debit" else -e.amount_minor
        totals[e.transaction_id] = totals.get(e.transaction_id, 0) + signed
    return {txn: total for txn, total in totals.items() if total}
