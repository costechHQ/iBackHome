"""Business rules for escrow. Owner: Gabriel.

Other features call the functions in this file; they never query this feature's tables directly.
Every function takes the database session as its first argument.

What other features call:

    from app.features.escrow import service as escrow

    release = await escrow.request_release(session, milestone.id, actor)   # Lilian, on approve
    account = await escrow.get_or_create_account(session, project_id)

Funding a milestone (spec "Money flow" steps 1-2):

    POST /projects/{id}/funding        -> create_funding_checkout()  (Stripe Checkout; no ledger yet)
    Stripe checkout.session.completed  -> fund_from_checkout()       (ledger + hold + funded + audit)
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from fastapi import Request
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base import payments as ledger
from app.base.payments import accounts
from app.base.payments.fees import fee_minor, funding_fee_bps
from app.base.payments.fx import FUNDING_CURRENCIES, foreign_minor_for_ngn, get_fx_source
from app.base.payments.models import PaymentEvent
from app.base.payments.stripe_checkout import CheckoutGateway, CheckoutRequest, LineItem
from app.base.users.models import User
from app.core.errors import AppError
from app.features.escrow.models import EscrowAccount
from app.features.escrow.providers import get_escrow_provider
from app.features.escrow.settings import get_escrow_settings
from app.features.milestones import service as milestones
from app.features.milestones.models import MilestoneStatus
from app.features.projects import service as projects

logger = logging.getLogger(__name__)

# The escrow partner holds naira; milestones are priced in naira.
ESCROW_CURRENCY = "NGN"

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


# --- funding: POST /projects/{id}/funding -----------------------------------------------------


@dataclass(frozen=True)
class FundingQuote:
    currency: str
    amount_ngn_minor: int  # what the escrow will hold
    net_minor: int  # amount_ngn_minor in `currency`, rounded up
    fee_minor: int
    fee_bps: int
    fx_rate: Decimal  # NGN per 1 unit of `currency`
    fx_as_of: datetime

    @property
    def total_minor(self) -> int:
        return self.net_minor + self.fee_minor


@dataclass(frozen=True)
class FundingCheckout:
    project_id: uuid.UUID
    milestone_id: uuid.UUID
    checkout_session_id: str
    checkout_url: str
    quote: FundingQuote


async def quote_funding(amount_ngn_minor: int, currency: str) -> FundingQuote:
    """What a client pays in `currency` for a milestone of `amount_ngn_minor`, fee included."""
    fx = await get_fx_source().ngn_per(currency)
    net = foreign_minor_for_ngn(amount_ngn_minor, fx.rate, currency)
    bps = funding_fee_bps()
    return FundingQuote(
        currency=currency,
        amount_ngn_minor=amount_ngn_minor,
        net_minor=net,
        fee_minor=fee_minor(net, bps),
        fee_bps=bps,
        fx_rate=fx.rate,
        fx_as_of=fx.as_of,
    )


def _funding_metadata(
    project_id: uuid.UUID, milestone_id: uuid.UUID, client_id: uuid.UUID, quote: FundingQuote
) -> dict[str, str]:
    """Stripe metadata (strings only). Comes back signed on the webhook; the handler trusts it."""
    return {
        "purpose": "milestone_funding",
        "project_id": str(project_id),
        "milestone_id": str(milestone_id),
        "client_id": str(client_id),
        "currency": quote.currency,
        "fx_rate": str(quote.fx_rate),
        "fx_as_of": quote.fx_as_of.isoformat(),
        "amount_ngn_minor": str(quote.amount_ngn_minor),
        "net_minor": str(quote.net_minor),
        "fee_minor": str(quote.fee_minor),
        "fee_bps": str(quote.fee_bps),
    }


async def create_funding_checkout(
    session: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
    currency: str,
    *,
    gateway: CheckoutGateway,
    idempotency_key: str | None = None,
    request: Request | None = None,
) -> FundingCheckout:
    """Start paying for a milestone: a Stripe Checkout session for its NGN amount plus our fee.

    - 404 project_not_found, milestone_not_found
    - 403 not_project_member, not_project_client (only the project's own client funds it)
    - 409 project_not_active, milestone_not_in_project, milestone_not_pending
    - 422 currency_not_supported; 502 stripe_unavailable

    Writes NO ledger entries: money only counts when Stripe's signed webhook confirms payment.
    Writes an audit entry. Does not commit.
    """
    if currency not in FUNDING_CURRENCIES:
        raise AppError(
            "currency_not_supported", f"Funding currency must be one of {FUNDING_CURRENCIES}.", 422
        )
    project = await projects.require_project_member(session, user, project_id)
    if project.client_id != user.id:
        raise AppError("not_project_client", "Only the project's client can fund its milestones.", 403)
    if project.status != "active":
        raise AppError(
            "project_not_active",
            f"Milestones can only be funded on an active project (this one is '{project.status}').",
            409,
        )
    milestone = await milestones.get_milestone(session, milestone_id)
    if milestone.project_id != project_id:
        raise AppError("milestone_not_in_project", "This milestone belongs to another project.", 409)
    if milestone.status != MilestoneStatus.PENDING:
        raise AppError(
            "milestone_not_pending",
            f"Only a pending milestone can be funded (this one is '{milestone.status.value}').",
            409,
        )
    if milestone.currency != ESCROW_CURRENCY:
        raise AppError("milestone_currency_unsupported", "Only naira milestones can be funded.", 409)

    quote = await quote_funding(milestone.amount_minor, currency)
    metadata = _funding_metadata(project_id, milestone_id, user.id, quote)
    line_items = [
        LineItem(f"{project.title}: milestone {milestone.sequence}, {milestone.name}", quote.net_minor)
    ]
    if quote.fee_minor:
        line_items.append(LineItem("iBackHome funding fee", quote.fee_minor))
    settings = get_escrow_settings()
    # {CHECKOUT_SESSION_ID} is Stripe's own placeholder: pass it through untouched.
    url_values = {
        "project_id": project_id,
        "milestone_id": milestone_id,
        "CHECKOUT_SESSION_ID": "{CHECKOUT_SESSION_ID}",
    }
    checkout = await gateway.create_checkout_session(
        CheckoutRequest(
            currency=currency,
            line_items=line_items,
            metadata=metadata,
            success_url=settings.funding_success_url.format(**url_values),
            cancel_url=settings.funding_cancel_url.format(**url_values),
            client_reference_id=str(milestone_id),
            customer_email=user.email,
            # Scoped to this milestone, so one header reused on another milestone can't collide in Stripe.
            idempotency_key=f"funding:{milestone_id}:{idempotency_key}" if idempotency_key else None,
        )
    )
    await audit.record(
        session,
        user.id,
        "funding.checkout_created",
        "milestone",
        milestone_id,
        after={**metadata, "checkout_session_id": checkout.id, "total_minor": quote.total_minor},
        request=request,
    )
    return FundingCheckout(project_id, milestone_id, checkout.id, checkout.url, quote)


# --- funding: Stripe checkout.session.completed ---------------------------------------------


class _FundingMetadata(BaseModel):
    """The metadata create_funding_checkout() put on the session (signed by Stripe on the way back)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    project_id: uuid.UUID
    milestone_id: uuid.UUID
    client_id: uuid.UUID
    currency: str
    fx_rate: Decimal
    amount_ngn_minor: int
    net_minor: int
    fee_minor: int
    fee_bps: int

    @field_validator("fx_rate")
    @classmethod
    def _positive_rate(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("fx_rate must be a positive decimal")
        return value


FundingOutcome = Literal["funded", "unmatched", "hold_pending", "ignored"]


@dataclass(frozen=True)
class FundingResult:
    outcome: FundingOutcome
    reason: str | None = None


async def fund_from_checkout(
    session: AsyncSession, event: PaymentEvent, request: Request | None = None
) -> FundingResult:
    """Record a paid Checkout session and hold the money in escrow, in the caller's transaction.

    Runs once per Stripe event (payment_events makes re-deliveries no-ops). Outcomes:

    - funded: T1 payment received (+ fee), T2 converted out, T3 held in escrow (fx_rate stored on
      T2 and T3); provider.hold() with ref "stripe_checkout:<session id>", so a retry never holds
      twice; escrow_accounts.balance_minor += amount; milestones.mark_funded(); audit escrow.funded.
    - unmatched: the money arrived but this milestone can't take it (no longer pending, another
      project, amounts disagree). Only T1 is written, gross, to client_funding, so our ledger still
      matches Stripe; audit funding.unmatched so ops can refund. No hold.
    - hold_pending: the partner will confirm the hold later. T1 only; the milestone stays pending
      until the partner's confirmation (escrow webhook, once a real partner exists).
    - ignored: not one of our funding sessions, or not paid yet (async payment methods send
      checkout.session.async_payment_succeeded later). Nothing written.

    If the escrow hold fails, the exception propagates: everything rolls back (the event row too),
    Stripe gets a 5xx and retries, and the retry holds with the same ref.
    """
    obj: dict[str, Any] = (event.payload.get("data") or {}).get("object") or {}
    raw_metadata = obj.get("metadata") or {}
    session_id = str(obj.get("id", ""))
    if raw_metadata.get("purpose") != "milestone_funding":
        logger.info("stripe checkout %s is not a milestone funding; ignored", session_id)
        return FundingResult("ignored", "not_milestone_funding")
    if obj.get("payment_status") != "paid":
        return FundingResult("ignored", "not_paid")
    try:
        meta = _FundingMetadata.model_validate(raw_metadata)
        paid_minor = int(obj["amount_total"])
        currency = str(obj["currency"]).upper()
    except (ValidationError, KeyError, TypeError, ValueError, InvalidOperation) as exc:
        # Signed by Stripe, so this is our bug, not an attacker: fail loudly and let Stripe retry.
        raise AppError(
            "funding_metadata_invalid", f"Checkout {session_id} has unusable funding data.", 422
        ) from exc

    milestone = await milestones.get_milestone(session, meta.milestone_id, lock=True)
    reason = _unmatched_reason(meta, milestone.project_id, milestone.status, milestone.amount_minor)
    reason = reason or _payment_mismatch(meta, paid_minor, currency)
    ref_id = event.id  # all transactions of one payment share the payment event as their ref

    if reason is not None:
        t1 = await ledger.post_transaction(
            session,
            [
                ledger.debit(accounts.stripe_clearing(currency), paid_minor, currency),
                ledger.credit(accounts.client_funding(meta.project_id, currency), paid_minor, currency),
            ],
            ref_type="payment_event",
            ref_id=ref_id,
        )
        await audit.record(
            session,
            None,
            "funding.unmatched",
            "milestone",
            meta.milestone_id,
            after=_audit_after(meta, session_id, event, paid_minor, [t1], reason=reason),
            request=request,
        )
        logger.warning("checkout %s paid but not applied (%s); ops must refund", session_id, reason)
        return FundingResult("unmatched", reason)

    hold = await get_escrow_provider().hold(
        meta.project_id, meta.amount_ngn_minor, ESCROW_CURRENCY, ref=f"stripe_checkout:{session_id}"
    )
    if hold.status == "failed":
        raise AppError("escrow_hold_failed", "The escrow partner refused the hold.", 502)

    received = [
        ledger.debit(accounts.stripe_clearing(currency), paid_minor, currency),
        ledger.credit(accounts.client_funding(meta.project_id, currency), meta.net_minor, currency),
    ]
    if meta.fee_minor:
        received.append(ledger.credit(accounts.fees(currency), meta.fee_minor, currency))
    t1 = await ledger.post_transaction(session, received, ref_type="payment_event", ref_id=ref_id)

    if hold.status == "pending":
        await audit.record(
            session,
            None,
            "funding.hold_pending",
            "milestone",
            meta.milestone_id,
            after=_audit_after(meta, session_id, event, paid_minor, [t1], hold_ref=hold.provider_ref),
            request=request,
        )
        return FundingResult("hold_pending")

    rate = meta.fx_rate
    t2 = await ledger.post_transaction(
        session,
        [
            ledger.debit(accounts.client_funding(meta.project_id, currency), meta.net_minor, currency, rate),
            ledger.credit(accounts.fx_conversion(currency), meta.net_minor, currency, rate),
        ],
        ref_type="payment_event",
        ref_id=ref_id,
    )
    ngn = meta.amount_ngn_minor
    t3 = await ledger.post_transaction(
        session,
        [
            ledger.debit(accounts.escrow(meta.project_id, ESCROW_CURRENCY), ngn, ESCROW_CURRENCY, rate),
            ledger.credit(accounts.fx_conversion(ESCROW_CURRENCY), ngn, ESCROW_CURRENCY, rate),
        ],
        ref_type="payment_event",
        ref_id=ref_id,
    )
    account = await get_or_create_account(session, meta.project_id, ESCROW_CURRENCY, lock=True)
    account.balance_minor += ngn
    await session.flush()

    await milestones.mark_funded(session, meta.milestone_id)
    await audit.record(
        session,
        None,
        "escrow.funded",
        "milestone",
        meta.milestone_id,
        after=_audit_after(
            meta,
            session_id,
            event,
            paid_minor,
            [t1, t2, t3],
            hold_ref=hold.provider_ref,
            escrow_balance_minor=account.balance_minor,
        ),
        request=request,
    )
    return FundingResult("funded")


def _unmatched_reason(
    meta: _FundingMetadata, project_id: uuid.UUID, status: MilestoneStatus, amount_minor: int
) -> str | None:
    if project_id != meta.project_id:
        return "milestone_not_in_project"
    if status != MilestoneStatus.PENDING:
        return f"milestone_{status.value}"
    if amount_minor != meta.amount_ngn_minor:
        return "milestone_amount_changed"
    return None


def _payment_mismatch(meta: _FundingMetadata, paid_minor: int, currency: str) -> str | None:
    if currency != meta.currency:
        return "currency_mismatch"
    if paid_minor != meta.net_minor + meta.fee_minor:
        return "amount_mismatch"
    return None


def _audit_after(
    meta: _FundingMetadata,
    session_id: str,
    event: PaymentEvent,
    paid_minor: int,
    transactions: list[uuid.UUID],
    *,
    reason: str | None = None,
    hold_ref: str | None = None,
    escrow_balance_minor: int | None = None,
) -> dict[str, Any]:
    after: dict[str, Any] = {
        **meta.model_dump(mode="json"),
        "checkout_session_id": session_id,
        "payment_event_id": event.id,
        "stripe_event_id": event.event_id,
        "paid_minor": paid_minor,
        "ledger_transaction_ids": transactions,
    }
    optional = {"reason": reason, "escrow_hold_ref": hold_ref, "escrow_balance_minor": escrow_balance_minor}
    after.update({key: value for key, value in optional.items() if value is not None})
    return after
