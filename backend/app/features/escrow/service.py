"""Business rules for escrow. Owner: Gabriel.

Other features call the functions in this file; they never query this feature's tables directly.
Every function takes the database session as its first argument.

What other features call:

    from app.features.escrow import service as escrow

    release = await escrow.request_release(session, milestone.id, actor)   # Lilian, on approve
    release_id = await escrow.pay_supplier(session, order.id)               # Abigail, on delivery
    account = await escrow.get_or_create_account(session, project_id)

Funding a milestone (spec "Money flow" steps 1-2):

    POST /projects/{id}/funding        -> create_funding_checkout()  (Stripe Checkout; no ledger yet)
    Stripe checkout.session.completed  -> fund_from_checkout()       (ledger + hold + funded + audit)

Releasing money (spec "Money flow" steps 3-4; release states requested -> submitted -> released | failed):

    request_release() / pay_supplier()  -> escrow_releases row `requested`; after commit, Celery
                                           escrow.submit_release (3 retries, then ops alert)
    submit_release()                    -> EscrowProvider.release(ref=release id); `released` at once
                                           (simulated) or `submitted` until the escrow webhook
    confirm_release()                   -> ledger (payable / escrow), cache, milestone released,
                                           audit, payout queued for Paystack
    payout outcome (on_payout_outcome)  -> ledger (escrow_payouts / payable); supplier order paid
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from fastapi import Request
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base import payments as ledger
from app.base.payments import accounts
from app.base.payments.after_commit import after_commit
from app.base.payments.fees import fee_minor, funding_fee_bps
from app.base.payments.fx import FUNDING_CURRENCIES, foreign_minor_for_ngn, get_fx_source
from app.base.payments.models import LedgerEntry, PaymentEvent, Payout
from app.base.payments.stripe_checkout import CheckoutGateway, CheckoutRequest, LineItem
from app.base.users.models import User
from app.core.errors import AppError
from app.features.escrow.models import Dispute, EscrowAccount, EscrowHold, EscrowRelease
from app.features.escrow.providers import get_escrow_provider
from app.features.escrow.settings import get_escrow_settings
from app.features.milestones import service as milestones
from app.features.milestones.models import Milestone, MilestoneStatus
from app.features.projects import service as projects
from app.features.suppliers import service as suppliers

logger = logging.getLogger(__name__)

# The escrow partner holds naira; milestones are priced in naira.
ESCROW_CURRENCY = "NGN"

# The spec's escrow release states: requested -> submitted -> released, or failed.
ReleaseStatus = Literal["requested", "submitted", "released", "failed"]


@dataclass(frozen=True)
class ReleaseRequest:
    release_id: uuid.UUID  # the escrow_releases row; use it to look the release up later
    milestone_id: uuid.UUID
    status: ReleaseStatus


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
    # The partner's hold id: a release of this money has to name it.
    session.add(
        EscrowHold(
            project_id=meta.project_id,
            milestone_id=meta.milestone_id,
            ref=hold.ref,
            provider_ref=hold.provider_ref,
            amount_minor=meta.amount_ngn_minor,
            currency=ESCROW_CURRENCY,
            status=hold.status,
        )
    )

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


# --- releases: money leaves escrow -------------------------------------------------------------

OPEN_RELEASE_STATUSES = ("requested", "submitted")
# Our Paystack reference for a release's payout: "rel_" + the release id in hex (36 characters).
PAYOUT_REFERENCE_PREFIX = "rel_"
# A release still `requested` this long after its last change was never queued, or its task died.
STALE_REQUEST = timedelta(minutes=10)


def payout_reference(release_id: uuid.UUID) -> str:
    return f"{PAYOUT_REFERENCE_PREFIX}{release_id.hex}"


def _payable_account(release: EscrowRelease) -> str:
    if release.milestone_id is not None:
        return accounts.contractor_payable(release.currency)
    return accounts.supplier_payable(release.currency)


def _payee(release: EscrowRelease) -> tuple[str, uuid.UUID]:
    kind, _, owner = release.payee.partition(":")
    return kind, uuid.UUID(owner)


async def get_release(session: AsyncSession, release_id: uuid.UUID, *, lock: bool = False) -> EscrowRelease:
    query = select(EscrowRelease).where(EscrowRelease.id == release_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    release = await session.scalar(query)
    if release is None:
        raise AppError("release_not_found", "Release not found.", 404)
    return release


async def _open_release(
    session: AsyncSession, *, milestone_id: uuid.UUID | None = None, order_id: uuid.UUID | None = None
) -> EscrowRelease | None:
    """The release of this milestone or order that has not failed (at most one: unique index)."""
    if milestone_id is not None:
        purpose = EscrowRelease.milestone_id == milestone_id
    else:
        purpose = EscrowRelease.order_id == order_id
    return await session.scalar(select(EscrowRelease).where(purpose, EscrowRelease.status != "failed"))


async def _hold_left(session: AsyncSession, hold: EscrowHold) -> int:
    used = await session.scalar(
        select(func.coalesce(func.sum(EscrowRelease.amount_minor), 0)).where(
            EscrowRelease.hold_id == hold.id, EscrowRelease.status != "failed"
        )
    )
    return hold.amount_minor - int(used or 0)


async def _pick_hold(
    session: AsyncSession,
    project_id: uuid.UUID,
    amount_minor: int,
    currency: str,
    *,
    prefer_milestone: uuid.UUID | None = None,
) -> EscrowHold:
    """A held deposit of this project with `amount_minor` left: the milestone's own first, then oldest.

    The project's holds are locked, so two releases can't both count the same money. Also checks
    the ledger (the source of truth): escrow balance minus releases still in flight.
    - 409 escrow_hold_missing: nothing of this project's money is held (never funded, or funded
      before escrow_holds existed)
    - 409 escrow_insufficient_funds
    """
    holds = list(
        await session.scalars(
            select(EscrowHold)
            .where(
                EscrowHold.project_id == project_id,
                EscrowHold.status == "held",
                EscrowHold.currency == currency,
            )
            .order_by(EscrowHold.created_at, EscrowHold.id)
            .with_for_update()
        )
    )
    if not holds:
        raise AppError("escrow_hold_missing", "No money is held in escrow for this project.", 409)
    in_flight = await session.scalar(
        select(func.coalesce(func.sum(EscrowRelease.amount_minor), 0)).where(
            EscrowRelease.project_id == project_id,
            EscrowRelease.currency == currency,
            EscrowRelease.status.in_(OPEN_RELEASE_STATUSES),
        )
    )
    available = await ledger.balance(session, accounts.escrow(project_id, currency)) - int(in_flight or 0)
    holds.sort(key=lambda h: h.milestone_id != prefer_milestone)  # stable: the milestone's own first
    for hold in holds:
        if available >= amount_minor and await _hold_left(session, hold) >= amount_minor:
            return hold
    raise AppError(
        "escrow_insufficient_funds",
        "Not enough of this project's money is left in escrow for this payment.",
        409,
    )


async def _create_release(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    hold: EscrowHold,
    payee: str,
    amount_minor: int,
    currency: str,
    milestone_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None,
) -> EscrowRelease:
    release = EscrowRelease(
        project_id=project_id,
        milestone_id=milestone_id,
        order_id=order_id,
        hold_id=hold.id,
        payee=payee,
        amount_minor=amount_minor,
        currency=currency,
        status="requested",
        attempts=0,
        requested_by=actor_id,
        requested_at=datetime.now(UTC),
    )
    session.add(release)
    await session.flush()
    await audit.record(
        session,
        actor_id,
        "escrow.release_requested",
        "escrow_release",
        release.id,
        after=audit.snapshot(release),
    )
    after_commit(session, enqueue_submit_release, release.id)
    return release


def enqueue_submit_release(release_id: uuid.UUID) -> None:
    """Queue escrow.submit_release (runs after commit; the sweeper re-queues it if this is lost)."""
    from app.features.escrow.tasks import submit_release_task

    submit_release_task.delay(str(release_id))


def _as_request(release: EscrowRelease) -> ReleaseRequest:
    assert release.milestone_id is not None
    status: ReleaseStatus = release.status  # type: ignore[assignment]  # the database checks it
    return ReleaseRequest(release_id=release.id, milestone_id=release.milestone_id, status=status)


async def request_release(session: AsyncSession, milestone_id: uuid.UUID, actor: User) -> ReleaseRequest:
    """Ask the escrow partner to release an approved milestone's money to the project's contractor.

    Inside the caller's transaction; never commits. Creates an `escrow_releases` row (`requested`)
    and, once the caller commits, queues escrow.submit_release, which calls the partner. The
    milestone becomes `released` only when the partner confirms (approved -> released is a system
    transition), and only then are the ledger entries written.

    Calling it again for the same milestone returns the existing release (even once released).
    A disputed milestone is released only through resolve_dispute() (two ops approvals).
    - 404 milestone_not_found / project_not_found
    - 409 dispute_open, milestone_not_approved, milestone_currency_unsupported,
      project_has_no_contractor, escrow_hold_missing, escrow_insufficient_funds
    """
    milestone = await milestones.get_milestone(session, milestone_id, lock=True)
    if await _open_dispute(session, milestone_id) is not None:
        raise AppError("dispute_open", "This milestone has an open dispute; it can't be released.", 409)
    existing = await _open_release(session, milestone_id=milestone_id)
    if existing is not None:
        return _as_request(existing)
    if milestone.status != MilestoneStatus.APPROVED:
        raise AppError(
            "milestone_not_approved",
            f"Only an approved milestone can be released (this one is '{milestone.status.value}').",
            409,
        )
    return await _release_to_contractor(session, milestone, actor.id)


async def _release_to_contractor(
    session: AsyncSession, milestone: Milestone, actor_id: uuid.UUID
) -> ReleaseRequest:
    if milestone.currency != ESCROW_CURRENCY:
        raise AppError("milestone_currency_unsupported", "Only naira milestones can be released.", 409)
    project = await projects.get_project(session, milestone.project_id)
    if project.contractor_id is None:
        raise AppError("project_has_no_contractor", "This project has no contractor to pay.", 409)
    hold = await _pick_hold(
        session, project.id, milestone.amount_minor, ESCROW_CURRENCY, prefer_milestone=milestone.id
    )
    release = await _create_release(
        session,
        project_id=project.id,
        hold=hold,
        payee=f"contractor:{project.contractor_id}",
        amount_minor=milestone.amount_minor,
        currency=ESCROW_CURRENCY,
        milestone_id=milestone.id,
        actor_id=actor_id,
    )
    return _as_request(release)


async def pay_supplier(session: AsyncSession, order_id: uuid.UUID) -> uuid.UUID:
    """Release a delivered order's total from the project's escrow to its supplier; returns the release id.

    Called by suppliers in the same transaction that marks the order `delivered`, so a delivery is
    never saved without its payment being started. The order becomes `paid` (suppliers.mark_paid)
    when Paystack confirms the supplier's payout. Calling it again returns the same release.
    - 404 order_not_found
    - 409 order_not_delivered, order_currency_unsupported, supplier_payout_not_set (the supplier
      has no bank account registered), escrow_hold_missing, escrow_insufficient_funds
    """
    order = await suppliers.get_order(session, order_id, lock=True)
    existing = await _open_release(session, order_id=order_id)
    if existing is not None:
        return existing.id
    if order.status != "delivered":
        raise AppError(
            "order_not_delivered", f"Only a delivered order can be paid (this one is '{order.status}').", 409
        )
    if order.currency != ESCROW_CURRENCY:
        raise AppError("order_currency_unsupported", "Only naira orders can be paid from escrow.", 409)
    if await ledger.get_recipient_for(session, supplier_id=order.supplier_id) is None:
        raise AppError(
            "supplier_payout_not_set", "This supplier has no bank account registered for payouts.", 409
        )
    hold = await _pick_hold(session, order.project_id, order.total_minor, ESCROW_CURRENCY)
    release = await _create_release(
        session,
        project_id=order.project_id,
        hold=hold,
        payee=f"supplier:{order.supplier_id}",
        amount_minor=order.total_minor,
        currency=ESCROW_CURRENCY,
        order_id=order.id,
        actor_id=None,
    )
    return release.id


async def submit_release(session: AsyncSession, release_id: uuid.UUID) -> EscrowRelease:
    """Send one release to the escrow partner (the escrow.submit_release task). Safe to run again.

    The release id is the partner's idempotency ref, so a retry never releases twice.
    - partner answers `released` (the simulated partner does): confirm_release() at once
    - `submitted`: the partner confirms later by webhook (release.succeeded / release.failed)
    - `failed`: fail_release() (ops alerted)
    - EscrowProviderError (unreachable) propagates; the task retries. Does not commit.
    """
    release = await get_release(session, release_id, lock=True)
    if release.status not in OPEN_RELEASE_STATUSES:
        return release
    hold = await session.get(EscrowHold, release.hold_id)
    if hold is None:  # pragma: no cover - foreign key
        raise AppError("escrow_hold_missing", "The release's hold is gone.", 409)
    release.attempts += 1
    result = await get_escrow_provider().release(
        hold.provider_ref, release.payee, release.amount_minor, ref=str(release.id)
    )
    if result.status == "failed":
        return await fail_release(session, release.id, "The escrow partner refused the release.")
    if result.status == "released":
        return await confirm_release(session, release.id, result.provider_ref)
    if release.status == "requested":
        before = audit.snapshot(release)
        release.status = "submitted"
        release.provider_ref = result.provider_ref
        await session.flush()
        await audit.record(
            session,
            None,
            "escrow.release_submitted",
            "escrow_release",
            release.id,
            before=before,
            after=audit.snapshot(release),
        )
    return release


async def confirm_release(
    session: AsyncSession, release_id: uuid.UUID, provider_ref: str | None, request: Request | None = None
) -> EscrowRelease:
    """The partner released the money: record it, all in the caller's transaction.

    - ledger: debit contractor_payable (or supplier_payable), credit escrow:{project} (ref escrow_release)
    - escrow_accounts.balance_minor reduced; release `released`
    - milestone approved -> released (milestones.mark_released)
    - audit escrow.released; the payee's Paystack payout queued (sent after commit). A payee with
      no bank account registered is left for ops (audit payout.awaiting_recipient, ops alert).
    Already released: nothing changes. A release we had marked `failed` is not changed either; it
    is logged for ops to reconcile (the partner moved money we had given up on).
    """
    release = await get_release(session, release_id, lock=True)
    if release.status == "released":
        return release
    if release.status == "failed":
        logger.error("OPS ALERT: escrow partner released %s, which we had marked failed", release.id)
        await audit.record(
            session,
            None,
            "escrow.release_confirmed_after_failure",
            "escrow_release",
            release.id,
            after={"provider_ref": provider_ref},
            request=request,
        )
        return release

    before = audit.snapshot(release)
    amount, currency = release.amount_minor, release.currency
    transaction_id = await ledger.post_transaction(
        session,
        [
            ledger.debit(_payable_account(release), amount, currency),
            ledger.credit(accounts.escrow(release.project_id, currency), amount, currency),
        ],
        ref_type="escrow_release",
        ref_id=release.id,
    )
    account = await get_or_create_account(session, release.project_id, currency, lock=True)
    account.balance_minor -= amount
    release.status = "released"
    release.released_at = datetime.now(UTC)
    release.provider_ref = provider_ref or release.provider_ref
    await session.flush()
    if release.milestone_id is not None:
        await _mark_milestone_released(session, release.milestone_id)
    await audit.record(
        session,
        None,
        "escrow.released",
        "escrow_release",
        release.id,
        before=before,
        after={
            **audit.snapshot(release),
            "ledger_transaction_id": transaction_id,
            "escrow_balance_minor": account.balance_minor,
        },
        request=request,
    )
    await _queue_payout(session, release, request)
    return release


async def _queue_payout(
    session: AsyncSession, release: EscrowRelease, request: Request | None
) -> Payout | None:
    kind, owner_id = _payee(release)
    if kind == "contractor":
        recipient = await ledger.get_recipient_for(session, user_id=owner_id)
    else:
        recipient = await ledger.get_recipient_for(session, supplier_id=owner_id)
    if recipient is None:
        logger.error(
            "OPS ALERT: release %s is released but %s has no payout account", release.id, release.payee
        )
        await audit.record(
            session,
            None,
            "payout.awaiting_recipient",
            "escrow_release",
            release.id,
            after={
                "payee": release.payee,
                "amount_minor": release.amount_minor,
                "currency": release.currency,
            },
            request=request,
        )
        return None
    what = "milestone" if release.milestone_id is not None else "materials order"
    return await ledger.queue_transfer(
        session,
        recipient.id,
        release.amount_minor,
        payout_reference(release.id),
        reason=f"iBackHome {what} payment",
        request=request,
    )


async def fail_release(
    session: AsyncSession, release_id: uuid.UUID, reason: str, request: Request | None = None
) -> EscrowRelease:
    """Give up on a release (partner refused, or unreachable after every retry) and alert ops.

    Only a `requested` or `submitted` release changes; the milestone stays `approved`, the money
    stays in escrow, and ops decide what happens next (spec: failed after 3 retries, ops alerted).
    """
    release = await get_release(session, release_id, lock=True)
    if release.status not in OPEN_RELEASE_STATUSES:
        return release
    before = audit.snapshot(release)
    release.status = "failed"
    release.failure_reason = reason[:500]
    await session.flush()
    await audit.record(
        session,
        None,
        "escrow.release_failed",
        "escrow_release",
        release.id,
        before=before,
        after=audit.snapshot(release),
        request=request,
    )
    logger.error("OPS ALERT: escrow release %s failed: %s", release.id, reason)
    return release


async def apply_release_event(
    session: AsyncSession, event: PaymentEvent, request: Request | None = None
) -> None:
    """The partner's release.succeeded / release.failed webhook (our scheme until a partner signs).

    Payload: {"id", "type", "data": {"ref": <our release id>, "provider_ref", "amount_minor", "reason"}}.
    An unknown ref or a different amount is logged and acknowledged, not raised (raising would make
    the partner retry an event we can never apply).
    """
    data: dict[str, Any] = event.payload.get("data") or {}
    try:
        release_id = uuid.UUID(str(data.get("ref")))
    except ValueError:
        logger.warning("escrow %s with unusable ref %r; ignored", event.event_type, data.get("ref"))
        return
    release = await session.get(EscrowRelease, release_id)
    if release is None:
        logger.warning("escrow %s for unknown release %s; ignored", event.event_type, release_id)
        return
    if event.event_type == "release.failed":
        reason = str(data.get("reason") or "The escrow partner failed the release.")
        await fail_release(session, release_id, reason, request)
        return
    amount = data.get("amount_minor")
    if amount is not None and amount != release.amount_minor:
        logger.error(
            "OPS ALERT: escrow confirmed %s for release %s, ours is %s; not applied",
            amount,
            release_id,
            release.amount_minor,
        )
        return
    provider_ref = data.get("provider_ref")
    await confirm_release(session, release_id, str(provider_ref) if provider_ref else None, request)


async def on_release_payout(
    session: AsyncSession, payout: Payout, previous: str, request: Request | None
) -> None:
    """A release's Paystack payout changed status (registered with payments.on_payout_outcome).

    - success: ledger debit escrow_payouts, credit the payable (the money reached the payee); a
      supplier order becomes `paid`
    - reversed after success: the opposite entry, ops alerted
    - failed (or reversed before success): ops alerted; the money stays in the payable account
    """
    try:
        release_id = uuid.UUID(hex=payout.reference.removeprefix(PAYOUT_REFERENCE_PREFIX))
    except ValueError:
        logger.warning("payout %s has a release reference we can't read; ignored", payout.reference)
        return
    release = await session.get(EscrowRelease, release_id)
    if release is None:
        logger.warning("payout %s for unknown release %s; ignored", payout.id, release_id)
        return
    payable = _payable_account(release)
    paid_out = accounts.escrow_payouts(payout.currency)
    after: dict[str, Any] = {"payout_id": payout.id, "payout_status": payout.status, "previous": previous}

    if payout.status == "success":
        after["ledger_transaction_id"] = await ledger.post_transaction(
            session,
            [
                ledger.debit(paid_out, payout.amount_minor, payout.currency),
                ledger.credit(payable, payout.amount_minor, payout.currency),
            ],
            ref_type="escrow_release",
            ref_id=release.id,
        )
        if release.order_id is not None:
            await suppliers.mark_paid(session, release.order_id)
        action = "escrow.payout_confirmed"
    elif payout.status == "reversed" and previous == "success":
        after["ledger_transaction_id"] = await ledger.post_transaction(
            session,
            [
                ledger.debit(payable, payout.amount_minor, payout.currency),
                ledger.credit(paid_out, payout.amount_minor, payout.currency),
            ],
            ref_type="escrow_release",
            ref_id=release.id,
        )
        action = "escrow.payout_reversed"
        logger.error("OPS ALERT: payout %s for release %s was reversed", payout.id, release.id)
    elif payout.status in ("failed", "reversed"):
        action = "escrow.payout_failed"
        logger.error("OPS ALERT: payout %s for release %s %s", payout.id, release.id, payout.status)
    else:
        return
    await audit.record(session, None, action, "escrow_release", release.id, after=after, request=request)


async def list_failed_releases(session: AsyncSession, limit: int = 50) -> list[EscrowRelease]:
    """Failed releases, newest first (for the ops queue)."""
    rows = await session.scalars(
        select(EscrowRelease)
        .where(EscrowRelease.status == "failed")
        .order_by(EscrowRelease.updated_at.desc(), EscrowRelease.id.desc())
        .limit(limit)
    )
    return list(rows)


async def list_stale_requests(
    session: AsyncSession, now: datetime | None = None, limit: int = 100
) -> list[uuid.UUID]:
    """Releases still `requested` long after their last change (never queued, or the task died)."""
    cutoff = (now or datetime.now(UTC)) - STALE_REQUEST
    rows = await session.scalars(
        select(EscrowRelease.id)
        .where(EscrowRelease.status == "requested", EscrowRelease.updated_at < cutoff)
        .order_by(EscrowRelease.updated_at)
        .limit(limit)
    )
    return list(rows)


# --- disputes (spec: open -> resolved_release | resolved_reject; two ops approvals) ------------

DisputeOutcome = Literal["release", "rework"]
_RESOLVED_STATUS: dict[str, str] = {"release": "resolved_release", "rework": "resolved_reject"}


async def _open_dispute(session: AsyncSession, milestone_id: uuid.UUID) -> Dispute | None:
    return await session.scalar(
        select(Dispute).where(Dispute.milestone_id == milestone_id, Dispute.status == "open")
    )


async def get_dispute(session: AsyncSession, dispute_id: uuid.UUID, *, lock: bool = False) -> Dispute:
    query = select(Dispute).where(Dispute.id == dispute_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    dispute = await session.scalar(query)
    if dispute is None:
        raise AppError("dispute_not_found", "Dispute not found.", 404)
    return dispute


async def raise_dispute(
    session: AsyncSession, user: User, milestone_id: uuid.UUID, reason: str, request: Request | None = None
) -> Dispute:
    """The project's client disputes a verified milestone: verified -> disputed, dispute `open`.

    The spec's API table also lists the contractor, but its milestone state machine lets only the
    client dispute (verified -> disputed), so a contractor is refused until that is settled.
    - 403 dispute_not_allowed (not a client), not_project_member, not_project_client
    - 404 milestone_not_found; 409 dispute_already_open, milestone_not_verified
    Audited (dispute.opened, plus milestone.disputed). Does not commit.
    """
    if user.role != "client":
        raise AppError("dispute_not_allowed", "Only the project's client can dispute a milestone.", 403)
    milestone = await milestones.get_milestone(session, milestone_id, lock=True)
    project = await projects.require_project_member(session, user, milestone.project_id)
    if project.client_id != user.id:
        raise AppError("not_project_client", "Only the project's client can dispute a milestone.", 403)
    if await _open_dispute(session, milestone_id) is not None:
        raise AppError("dispute_already_open", "This milestone already has an open dispute.", 409)
    if milestone.status != MilestoneStatus.VERIFIED:
        raise AppError(
            "milestone_not_verified",
            f"Only a verified milestone can be disputed (this one is '{milestone.status.value}').",
            409,
        )
    dispute = Dispute(
        project_id=project.id,
        milestone_id=milestone.id,
        raised_by=user.id,
        reason=reason.strip()[:2000],
        status="open",
    )
    session.add(dispute)
    await session.flush()
    await milestones.mark_disputed(session, milestone.id, user.id)
    await audit.record(
        session,
        user.id,
        "dispute.opened",
        "dispute",
        dispute.id,
        after=audit.snapshot(dispute),
        request=request,
    )
    return dispute


@dataclass(frozen=True)
class DisputeResolution:
    dispute: Dispute
    resolved: bool  # False: the first ops approval is recorded; a second ops user must confirm
    release_id: uuid.UUID | None = None  # set when resolved for release


async def resolve_dispute(
    session: AsyncSession,
    ops_user: User,
    dispute_id: uuid.UUID,
    outcome: DisputeOutcome,
    notes: str,
    request: Request | None = None,
) -> DisputeResolution:
    """Two different ops users resolve a dispute: the first proposes, the second confirms.

    - First call: records the proposal; the dispute stays `open`.
    - Second call, by another ops user, same outcome:
      - rework: dispute `resolved_reject`, milestone disputed -> funded (mark_resolved "rework");
        the contractor fixes the work and claims again
      - release: dispute `resolved_release`, and a release to the contractor is requested; the
        milestone becomes released (mark_resolved "release") when escrow confirms, so `released`
        always means the money moved
    - 403 forbidden_role (not ops); 404 dispute_not_found
    - 409 dispute_not_open, second_approval_required (same ops user again), resolution_mismatch
      (the second ops user chose another outcome: the proposal stands; discuss, then confirm)
    Audited. Does not commit.
    """
    if ops_user.role != "ops":
        raise AppError("forbidden_role", "Only ops can resolve a dispute.", 403)
    if outcome not in _RESOLVED_STATUS:
        raise AppError("invalid_outcome", "Outcome must be 'release' or 'rework'.", 422)
    dispute = await get_dispute(session, dispute_id, lock=True)
    if dispute.status != "open":
        raise AppError("dispute_not_open", f"This dispute is already {dispute.status}.", 409)
    before = audit.snapshot(dispute)
    notes = notes.strip()

    if dispute.proposed_by is None:
        dispute.proposed_outcome = outcome
        dispute.proposed_by = ops_user.id
        dispute.proposed_at = datetime.now(UTC)
        dispute.resolution_notes = notes[:4000]
        await session.flush()
        await audit.record(
            session,
            ops_user.id,
            "dispute.resolution_proposed",
            "dispute",
            dispute.id,
            before=before,
            after=audit.snapshot(dispute),
            request=request,
        )
        return DisputeResolution(dispute, resolved=False)

    if dispute.proposed_by == ops_user.id:
        raise AppError("second_approval_required", "A different ops user must confirm this resolution.", 409)
    if dispute.proposed_outcome != outcome:
        raise AppError(
            "resolution_mismatch",
            f"The first ops approval was '{dispute.proposed_outcome}'; both approvals must agree.",
            409,
        )

    dispute.status = _RESOLVED_STATUS[outcome]
    dispute.resolved_by = ops_user.id
    if notes:
        dispute.resolution_notes = f"{dispute.resolution_notes or ''}\n---\n{notes}".strip()[:4000]
    await session.flush()
    release_id: uuid.UUID | None = None
    if outcome == "rework":
        await milestones.mark_resolved(session, dispute.milestone_id, "rework", ops_user.id)
    else:
        milestone = await milestones.get_milestone(session, dispute.milestone_id, lock=True)
        release_id = (await _release_to_contractor(session, milestone, ops_user.id)).release_id
    await audit.record(
        session,
        ops_user.id,
        "dispute.resolved",
        "dispute",
        dispute.id,
        before=before,
        after={**audit.snapshot(dispute), "release_id": release_id},
        request=request,
    )
    return DisputeResolution(dispute, resolved=True, release_id=release_id)


async def _mark_milestone_released(session: AsyncSession, milestone_id: uuid.UUID) -> None:
    """approved -> released (system), or disputed -> released for a dispute ops resolved for release."""
    milestone = await milestones.get_milestone(session, milestone_id, lock=True)
    if milestone.status != MilestoneStatus.DISPUTED:
        await milestones.mark_released(session, milestone_id)
        return
    dispute = await session.scalar(
        select(Dispute)
        .where(Dispute.milestone_id == milestone_id, Dispute.status == "resolved_release")
        .order_by(Dispute.updated_at.desc())
        .limit(1)
    )
    if dispute is None or dispute.resolved_by is None:
        raise AppError("dispute_not_resolved", "This disputed milestone was not resolved for release.", 409)
    await milestones.mark_resolved(session, milestone_id, "release", dispute.resolved_by)


async def list_open_disputes(session: AsyncSession, limit: int = 50) -> list[Dispute]:
    """Open disputes, oldest first (for Abigail's /ops/queue). Each has id, project_id,
    milestone_id, reason, created_at, and proposed_by once the first ops approval is in."""
    rows = await session.scalars(
        select(Dispute).where(Dispute.status == "open").order_by(Dispute.created_at, Dispute.id).limit(limit)
    )
    return list(rows)


# --- GET /projects/{id}/ledger -----------------------------------------------------------------


async def project_ledger(
    session: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[list[LedgerEntry], str | None]:
    """Funding, releases and payouts of one project, newest first: for its client and ops (spec).

    Every entry of every transaction that touches the project's accounts (client_funding, escrow)
    or one of its releases (whose payout entries are on the shared payable accounts).
    - 404 project_not_found; 403 not_project_member, not_project_client
    """
    project = await projects.require_project_member(session, user, project_id)
    if user.role != "ops" and project.client_id != user.id:
        raise AppError("not_project_client", "Only the project's client and ops can see its ledger.", 403)
    release_ids = await session.scalars(
        select(EscrowRelease.id).where(EscrowRelease.project_id == project_id)
    )
    return await ledger.list_entries_touching(
        session,
        account_prefixes=accounts.project_prefixes(project_id),
        refs=[("escrow_release", release_id) for release_id in release_ids],
        since=since,
        until=until,
        cursor=cursor,
        limit=limit,
    )
