"""Business rules for payments. Owner: Gabriel.

Other features call the functions in this file; they never query this feature's tables directly.
Every function takes the database session as its first argument.

The ledger is double-entry: every money event is one transaction (one `transaction_id`) made of
two or more entries in a single currency whose debits equal its credits.

Sign convention for `balance()`: debits minus credits. Asset accounts (`stripe_clearing`,
`escrow`, `escrow_payouts`) are positive when they hold money; accounts that record what we owe
or have received (`client_funding`, `contractor_payable`, `supplier_payable`, `fees`) are
negative while money sits in them.

    from app.base.payments import accounts, credit, debit, post_transaction

    txn_id = await post_transaction(
        session,
        [debit(accounts.stripe_clearing("GBP"), 100_000, "GBP"),
         credit(accounts.client_funding(project_id, "GBP"), 100_000, "GBP")],
        ref_type="payment_event",
        ref_id=event.id,
    )
    # ... change state, write audit log, then the caller commits once.
"""

import base64
import binascii
import logging
import re
import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from fastapi import Request
from sqlalchemy import case, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.payments.after_commit import after_commit
from app.base.payments.models import LedgerEntry, PaymentEvent, Payout, PayoutRecipient
from app.base.payments.paystack import PaystackClient, TransferResult, get_paystack_client
from app.core import pagination
from app.core.errors import AppError

logger = logging.getLogger(__name__)

Direction = Literal["debit", "credit"]
Provider = Literal["stripe", "paystack", "escrow"]

_CURRENCY = re.compile(r"^[A-Z]{3}$")
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class Entry:
    """One line of a ledger transaction. Build with `debit()` / `credit()`."""

    account: str
    direction: Direction
    amount_minor: int
    currency: str
    fx_rate: Decimal | None = None


def debit(account: str, amount_minor: int, currency: str, fx_rate: Decimal | None = None) -> Entry:
    return Entry(account, "debit", amount_minor, currency, fx_rate)


def credit(account: str, amount_minor: int, currency: str, fx_rate: Decimal | None = None) -> Entry:
    return Entry(account, "credit", amount_minor, currency, fx_rate)


@dataclass(frozen=True)
class EntryPage:
    items: list[LedgerEntry]
    next_cursor: str | None


def _check_entry(entry: Entry) -> None:
    # bool is a subclass of int; True must never mean "1 kobo".
    if type(entry.amount_minor) is not int or entry.amount_minor <= 0:
        raise AppError(
            "ledger_invalid_amount",
            f"amount_minor must be a positive integer, got {entry.amount_minor!r}.",
            422,
        )
    if entry.direction not in ("debit", "credit"):
        raise AppError(
            "ledger_invalid_entry", f"direction must be debit or credit, got {entry.direction!r}.", 422
        )
    if not isinstance(entry.currency, str) or not _CURRENCY.match(entry.currency):
        raise AppError("ledger_invalid_entry", f"currency must be ISO 4217, got {entry.currency!r}.", 422)
    if not entry.account or not isinstance(entry.account, str):
        raise AppError("ledger_invalid_entry", "account is required.", 422)
    if entry.fx_rate is not None and (
        not isinstance(entry.fx_rate, Decimal) or not entry.fx_rate.is_finite() or entry.fx_rate <= 0
    ):
        raise AppError("ledger_invalid_entry", "fx_rate must be a positive Decimal (never a float).", 422)


async def post_transaction(
    session: AsyncSession, entries: Sequence[Entry], *, ref_type: str, ref_id: uuid.UUID
) -> uuid.UUID:
    """Write one balanced transaction and return its transaction_id.

    Does not commit: the entries join the caller's database transaction, so the caller can
    write ledger + state change + audit log and commit once. The database re-checks the
    balance at commit (deferred trigger), so a bug here still cannot store an unbalanced ledger.
    """
    if len(entries) < 2:
        raise AppError("ledger_unbalanced", "A transaction needs at least two entries.", 422)
    if not ref_type:
        raise AppError("ledger_invalid_entry", "ref_type is required.", 422)
    for entry in entries:
        _check_entry(entry)

    currencies = {e.currency for e in entries}
    if len(currencies) != 1:
        raise AppError(
            "ledger_mixed_currency",
            f"All entries in a transaction must share one currency, got {sorted(currencies)}.",
            422,
        )

    debits = sum(e.amount_minor for e in entries if e.direction == "debit")
    credits = sum(e.amount_minor for e in entries if e.direction == "credit")
    if debits != credits:
        raise AppError("ledger_unbalanced", f"Debits ({debits}) must equal credits ({credits}).", 422)

    transaction_id = uuid.uuid4()
    session.add_all(
        LedgerEntry(
            transaction_id=transaction_id,
            account=e.account,
            direction=e.direction,
            amount_minor=e.amount_minor,
            currency=e.currency,
            fx_rate=e.fx_rate,
            ref_type=ref_type,
            ref_id=ref_id,
        )
        for e in entries
    )
    await session.flush()
    return transaction_id


async def balance(session: AsyncSession, account: str) -> int:
    """Debits minus credits for one account, in minor units (see sign convention above).

    Returns 0 for an account with no entries.
    """
    signed = case(
        (LedgerEntry.direction == "debit", LedgerEntry.amount_minor),
        else_=-LedgerEntry.amount_minor,
    )
    row = (
        await session.execute(
            select(func.count(func.distinct(LedgerEntry.currency)), func.coalesce(func.sum(signed), 0)).where(
                LedgerEntry.account == account
            )
        )
    ).one()
    currency_count, total = row
    if currency_count > 1:
        raise AppError("ledger_mixed_currency", f"Account {account!r} holds more than one currency.", 422)
    # Postgres returns SUM(bigint) as NUMERIC (a Decimal here); int() of an integral Decimal is exact.
    return int(total)


def _encode_cursor(entry: LedgerEntry) -> str:
    raw = f"{entry.created_at.isoformat()}|{entry.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        created_at, entry_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(created_at), uuid.UUID(entry_id)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise AppError("invalid_cursor", "The cursor is not valid.", 422) from exc


async def list_entries(
    session: AsyncSession,
    *,
    account: str | None = None,
    ref_type: str | None = None,
    ref_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> EntryPage:
    """Ledger entries oldest first, filtered, one page at a time.

    `since` is inclusive and `until` exclusive (both on created_at, UTC). Pass the returned
    `next_cursor` back to get the following page; it is None on the last page.
    """
    if not 1 <= limit <= MAX_PAGE_SIZE:
        raise AppError("invalid_limit", f"limit must be between 1 and {MAX_PAGE_SIZE}.", 422)

    query = select(LedgerEntry)
    if account is not None:
        query = query.where(LedgerEntry.account == account)
    if ref_type is not None:
        query = query.where(LedgerEntry.ref_type == ref_type)
    if ref_id is not None:
        query = query.where(LedgerEntry.ref_id == ref_id)
    if since is not None:
        query = query.where(LedgerEntry.created_at >= since)
    if until is not None:
        query = query.where(LedgerEntry.created_at < until)
    if cursor is not None:
        after = _decode_cursor(cursor)
        query = query.where(tuple_(LedgerEntry.created_at, LedgerEntry.id) > tuple_(*after))

    query = query.order_by(LedgerEntry.created_at, LedgerEntry.id).limit(limit + 1)
    rows = list((await session.scalars(query)).all())
    has_more = len(rows) > limit
    items = rows[:limit]
    return EntryPage(items=items, next_cursor=_encode_cursor(items[-1]) if has_more else None)


# --- payment_events: each webhook is processed once -----------------------------------------


class EventResult(StrEnum):
    NEW = "new"  # first delivery: process it
    DUPLICATE = "duplicate"  # stored before: acknowledge and do nothing


async def record_event(
    session: AsyncSession,
    provider: Provider,
    event_id: str,
    event_type: str,
    payload: Mapping[str, Any],
) -> tuple[EventResult, PaymentEvent | None]:
    """Store a verified webhook once. Returns (NEW, event) the first time, (DUPLICATE, None) after.

    INSERT ... ON CONFLICT DO NOTHING: when two deliveries race, the second waits on the unique
    index until the first commits (then sees DUPLICATE) or rolls back (then gets NEW and processes
    it itself). Does not commit: the caller records the event, writes ledger + state + audit, and
    commits once, so a failed handler leaves no event row and the provider's retry is processed.
    """
    if not event_id or not event_type:
        raise AppError("webhook_invalid_event", "The webhook has no event id or type.", 400)
    inserted_id = await session.scalar(
        insert(PaymentEvent)
        .values(
            id=uuid.uuid4(),
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payload=dict(payload),
        )
        .on_conflict_do_nothing(constraint="uq_payment_events_provider_event_id")
        .returning(PaymentEvent.id)
    )
    if inserted_id is None:
        return EventResult.DUPLICATE, None
    event = await session.get(PaymentEvent, inserted_id)
    assert event is not None
    return EventResult.NEW, event


async def mark_processed(session: AsyncSession, event: PaymentEvent) -> None:
    """Stamp the event as handled (same transaction as the handler's work)."""
    event.processed_at = datetime.now(UTC)
    await session.flush()


# --- Paystack payouts: recipients and transfers -----------------------------------------------

PayoutStatus = Literal["pending", "success", "failed", "reversed"]

_NUBAN = re.compile(r"^[0-9]{10}$")  # Nigerian bank account numbers are 10 digits
_BANK_CODE = re.compile(r"^[0-9A-Za-z]{2,10}$")
# Paystack's rule for transfer references: 16-50 chars of lower-case letters, digits, - and _.
_REFERENCE = re.compile(r"^[a-z0-9_-]{16,50}$")

# Paystack transfer webhooks and the payout status each one means.
TRANSFER_EVENTS: dict[str, PayoutStatus] = {
    "transfer.success": "success",
    "transfer.failed": "failed",
    "transfer.reversed": "reversed",
}
_PAYOUT_TRANSITIONS: set[tuple[str, str]] = {
    ("pending", "success"),
    ("pending", "failed"),
    ("pending", "reversed"),
    ("success", "reversed"),
}


def mask_account_number(account_number_or_last4: str) -> str:
    """'0123456789' -> '******6789'. The only form of an account number we ever store or log."""
    return "******" + account_number_or_last4[-4:]


async def register_payout_recipient(
    session: AsyncSession,
    *,
    account_name: str,
    account_number: str,
    bank_code: str,
    actor_id: uuid.UUID | None,
    user_id: uuid.UUID | None = None,
    supplier_id: uuid.UUID | None = None,
    client: PaystackClient | None = None,
    request: Request | None = None,
) -> PayoutRecipient:
    """Register a contractor's (user_id) or supplier's (supplier_id) bank account with Paystack.

    The full account number goes to Paystack and nowhere else: we keep the recipient_code,
    bank name, account name and the masked number. Registering the same account again for the
    same owner returns the existing row (Paystack returns the same recipient_code).

    - 422 recipient_owner_required, invalid_account_number, invalid_bank_code, paystack_refused
    - 409 recipient_belongs_to_another (that account is already registered to someone else)
    - 502 paystack_unavailable; 503 paystack_not_configured
    Writes an audit entry. Does not commit.
    """
    if (user_id is None) == (supplier_id is None):
        raise AppError("recipient_owner_required", "Give exactly one of user_id or supplier_id.", 422)
    account_number = account_number.strip()
    if not _NUBAN.match(account_number):
        raise AppError("invalid_account_number", "The account number must be 10 digits.", 422)
    if not _BANK_CODE.match(bank_code):
        raise AppError("invalid_bank_code", "The bank code is not valid.", 422)
    account_name = account_name.strip()
    if not account_name:
        raise AppError("invalid_account_name", "The account name is required.", 422)

    paystack = client or get_paystack_client()
    result = await paystack.create_transfer_recipient(account_name, account_number, bank_code)

    existing = await session.scalar(
        select(PayoutRecipient).where(PayoutRecipient.recipient_code == result.recipient_code)
    )
    if existing is not None:
        if (existing.user_id, existing.supplier_id) != (user_id, supplier_id):
            raise AppError(
                "recipient_belongs_to_another",
                "This bank account is already registered to someone else.",
                409,
            )
        return existing

    recipient = PayoutRecipient(
        user_id=user_id,
        supplier_id=supplier_id,
        provider="paystack",
        recipient_code=result.recipient_code,
        bank_code=result.bank_code,
        bank_name=result.bank_name,
        account_name=result.account_name,
        account_number_masked=mask_account_number(result.account_last4),
        currency="NGN",
    )
    session.add(recipient)
    await session.flush()
    await audit.record(
        session,
        actor_id,
        "payout_recipient.created",
        "payout_recipient",
        recipient.id,
        after=audit.snapshot(recipient),
        request=request,
    )
    return recipient


async def get_payout_recipient(session: AsyncSession, recipient_code: str) -> PayoutRecipient:
    recipient = await session.scalar(
        select(PayoutRecipient).where(PayoutRecipient.recipient_code == recipient_code)
    )
    if recipient is None:
        raise AppError("recipient_not_found", "No payout recipient with that code.", 404)
    return recipient


async def _start_or_find_transfer(
    paystack: PaystackClient, amount_minor: int, recipient_code: str, reference: str, reason: str
) -> TransferResult:
    """Start a transfer; if Paystack refuses or can't be reached, look it up by our reference.

    Found: that transfer (a lost answer, or a retry of a transfer Paystack already has). Not
    found: the original error (paystack_unavailable: try again later; paystack_refused: it was
    really refused). The lookup itself may raise paystack_unavailable.
    """
    try:
        return await paystack.initiate_transfer(amount_minor, recipient_code, reference, reason)
    except AppError as exc:
        if exc.code not in ("paystack_refused", "paystack_unavailable"):
            raise
        found = await paystack.verify_transfer(reference)
        if found is None:
            raise
        return found


async def initiate_transfer(
    session: AsyncSession,
    recipient_code: str,
    amount_minor: int,
    reference: str,
    *,
    reason: str,
    actor_id: uuid.UUID | None = None,
    client: PaystackClient | None = None,
    request: Request | None = None,
) -> Payout:
    """Send `amount_minor` kobo to a recipient through Paystack, idempotent on OUR `reference`.

    Calling again with the same reference and details returns the existing payout without a
    second Paystack call; the same reference with other details is refused (409). Paystack
    itself also refuses a reference it has seen, so even a lost answer can't pay twice: if
    Paystack's answer is lost (the caller's transaction then rolls back this row) or it refuses
    the reference on a retry, the transfer is looked up by reference and that result is kept.
    The payout starts `pending` (or `success`/`failed` if Paystack answers so at once);
    transfer.* webhooks move it on. Money leaving escrow uses queue_transfer() instead, which
    saves the payout before Paystack is called.

    - 404 recipient_not_found; 409 payout_reference_conflict, payout_in_progress
    - 422 invalid_amount, invalid_reference, paystack_refused; 502 paystack_unavailable
    Writes an audit entry. Does not commit.
    """
    if type(amount_minor) is not int or amount_minor <= 0:
        raise AppError(
            "invalid_amount", f"amount_minor must be a positive integer, got {amount_minor!r}.", 422
        )
    if not _REFERENCE.match(reference):
        raise AppError("invalid_reference", "reference must be 16-50 of a-z, 0-9, hyphen or underscore.", 422)
    recipient = await get_payout_recipient(session, recipient_code)

    existing = await session.scalar(select(Payout).where(Payout.reference == reference))
    if existing is not None:
        if (existing.recipient_id, existing.amount_minor) != (recipient.id, amount_minor):
            raise AppError("payout_reference_conflict", "This reference was used for another payout.", 409)
        return existing

    payout = Payout(
        recipient_id=recipient.id,
        provider="paystack",
        reference=reference,
        amount_minor=amount_minor,
        currency="NGN",
        reason=reason[:200],
        status="pending",
    )
    try:
        # The savepoint turns a racing duplicate (same reference, same moment) into a clean 409.
        async with session.begin_nested():
            session.add(payout)
    except IntegrityError as exc:
        raise AppError(
            "payout_in_progress", "A payout with this reference is already being sent.", 409
        ) from exc

    paystack = client or get_paystack_client()
    result = await _start_or_find_transfer(
        paystack, amount_minor, recipient.recipient_code, reference, payout.reason
    )
    payout.provider_transfer_code = result.transfer_code or None
    payout.status = result.status
    if result.status != "pending":
        payout.completed_at = datetime.now(UTC)
    await session.flush()
    await audit.record(
        session,
        actor_id,
        "payout.initiated",
        "payout",
        payout.id,
        after=audit.snapshot(payout),
        request=request,
    )
    return payout


async def apply_transfer_event(
    session: AsyncSession, event: PaymentEvent, request: Request | None = None
) -> Payout | None:
    """Move a payout on from a Paystack transfer.success / transfer.failed / transfer.reversed.

    Idempotent: a status the payout already has changes nothing. An unknown reference or an
    impossible move (e.g. reversed -> success) is logged and acknowledged, not raised: raising
    would make Paystack retry an event we can never apply. Writes an audit entry on a change.
    """
    new_status = TRANSFER_EVENTS[event.event_type]
    data: dict[str, Any] = event.payload.get("data") or {}
    reference = str(data.get("reference") or "")
    payout = await session.scalar(
        select(Payout)
        .where(Payout.reference == reference)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if payout is None:
        logger.warning("paystack %s for unknown reference %r; ignored", event.event_type, reference)
        return None
    if payout.status == new_status:
        return payout
    if (payout.status, new_status) not in _PAYOUT_TRANSITIONS:
        logger.warning("payout %s cannot move %s -> %s; ignored", payout.id, payout.status, new_status)
        return payout
    paystack_amount = data.get("amount")
    if paystack_amount is not None and paystack_amount != payout.amount_minor:
        logger.error(
            "payout %s: Paystack amount %s != ours %s", payout.id, paystack_amount, payout.amount_minor
        )

    before = audit.snapshot(payout)
    payout.status = new_status
    payout.completed_at = datetime.now(UTC)
    if not payout.provider_transfer_code and data.get("transfer_code"):
        payout.provider_transfer_code = str(data["transfer_code"])
    if new_status == "failed":
        payout.failure_reason = str(data.get("gateway_response") or data.get("message") or "failed")[:500]
    await session.flush()
    await audit.record(
        session,
        None,
        f"payout.{new_status}",
        "payout",
        payout.id,
        before=before,
        after={
            **audit.snapshot(payout),
            "paystack_event_id": event.event_id,
            "paystack_amount": paystack_amount,
        },
        request=request,
    )
    await _payout_changed(session, payout, before["status"], request)
    return payout


# --- payouts saved before Paystack is called ------------------------------------------------
#
# initiate_transfer() calls Paystack inside the caller's transaction, so a lost answer rolls the
# payout row back. Money that leaves escrow uses the two steps below instead: queue_transfer()
# saves a `pending` payout with no transfer code in the caller's transaction, and the Celery task
# payments.send_transfer runs send_transfer() once that has committed. "Pending without a transfer
# code" means "Paystack may or may not have it": sending again with the same reference is safe,
# and verify_transfer(reference) tells us what Paystack did with the first try.

PayoutListener = Callable[[AsyncSession, Payout, str, Request | None], Awaitable[None]]

_PAYOUT_LISTENERS: dict[str, PayoutListener] = {}


def on_payout_outcome(reference_prefix: str) -> Callable[[PayoutListener], PayoutListener]:
    """Register a function told about every status change of payouts whose reference starts so.

    Called as listener(session, payout, previous_status, request) in the transaction that changed
    the status (the transfer webhook's, or send_transfer's), so its ledger and state changes land
    with it or not at all.
    """

    def register(listener: PayoutListener) -> PayoutListener:
        existing = _PAYOUT_LISTENERS.get(reference_prefix)
        if existing is not None and existing is not listener:
            raise RuntimeError(
                f"payouts {reference_prefix!r} already have a listener: {existing.__qualname__}"
            )
        _PAYOUT_LISTENERS[reference_prefix] = listener
        return listener

    return register


async def _payout_changed(
    session: AsyncSession, payout: Payout, previous: str, request: Request | None
) -> None:
    for prefix, listener in _PAYOUT_LISTENERS.items():
        if payout.reference.startswith(prefix):
            await listener(session, payout, previous, request)


async def get_recipient_for(
    session: AsyncSession, *, user_id: uuid.UUID | None = None, supplier_id: uuid.UUID | None = None
) -> PayoutRecipient | None:
    """The newest payout recipient of a user (contractor) or a supplier, or None."""
    if (user_id is None) == (supplier_id is None):
        raise AppError("recipient_owner_required", "Give exactly one of user_id or supplier_id.", 422)
    owner = PayoutRecipient.user_id == user_id if user_id else PayoutRecipient.supplier_id == supplier_id
    return await session.scalar(
        select(PayoutRecipient)
        .where(owner)
        .order_by(PayoutRecipient.created_at.desc(), PayoutRecipient.id.desc())
        .limit(1)
    )


async def get_payout(session: AsyncSession, payout_id: uuid.UUID, *, lock: bool = False) -> Payout:
    query = select(Payout).where(Payout.id == payout_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    payout = await session.scalar(query)
    if payout is None:
        raise AppError("payout_not_found", "Payout not found.", 404)
    return payout


async def queue_transfer(
    session: AsyncSession,
    recipient_id: uuid.UUID,
    amount_minor: int,
    reference: str,
    *,
    reason: str,
    actor_id: uuid.UUID | None = None,
    request: Request | None = None,
) -> Payout:
    """Save a `pending` payout (no Paystack call) and send it once the caller has committed.

    Idempotent on `reference` like initiate_transfer(): the same reference and details return the
    existing payout; other details are refused (409 payout_reference_conflict).
    Writes an audit entry. Does not commit.
    """
    if type(amount_minor) is not int or amount_minor <= 0:
        raise AppError(
            "invalid_amount", f"amount_minor must be a positive integer, got {amount_minor!r}.", 422
        )
    if not _REFERENCE.match(reference):
        raise AppError("invalid_reference", "reference must be 16-50 of a-z, 0-9, hyphen or underscore.", 422)
    existing = await session.scalar(select(Payout).where(Payout.reference == reference))
    if existing is not None:
        if (existing.recipient_id, existing.amount_minor) != (recipient_id, amount_minor):
            raise AppError("payout_reference_conflict", "This reference was used for another payout.", 409)
        return existing

    payout = Payout(
        recipient_id=recipient_id,
        provider="paystack",
        reference=reference,
        amount_minor=amount_minor,
        currency="NGN",
        reason=reason[:200],
        status="pending",
    )
    session.add(payout)
    await session.flush()
    await audit.record(
        session, actor_id, "payout.queued", "payout", payout.id, after=audit.snapshot(payout), request=request
    )
    after_commit(session, enqueue_send_transfer, payout.id)
    return payout


def enqueue_send_transfer(payout_id: uuid.UUID) -> None:
    """Queue payments.send_transfer (runs after commit; the sweeper re-queues it if this is lost)."""
    from app.base.payments.tasks import send_transfer_task

    send_transfer_task.delay(str(payout_id))


async def send_transfer(
    session: AsyncSession, payout_id: uuid.UUID, *, client: PaystackClient | None = None
) -> Payout:
    """Send one queued payout to Paystack. Safe to run again at any time.

    - Not `pending`, or Paystack already gave it a transfer code: nothing to do.
    - Paystack answers: save its transfer code and status.
    - Paystack refuses or can't be reached: ask it for the transfer under our reference (a lost
      answer, or a retry of a transfer it already has). Found: save that. Not found and refused:
      the payout is `failed`. Not found and unreachable: raise, so the task retries.
    A change to success/failed is passed to the payout listeners in this transaction. Does not commit.
    """
    payout = await get_payout(session, payout_id, lock=True)
    if payout.status != "pending" or payout.provider_transfer_code:
        return payout
    recipient = await session.get(PayoutRecipient, payout.recipient_id)
    if recipient is None:  # pragma: no cover - foreign key
        raise AppError("recipient_not_found", "No payout recipient for this payout.", 404)

    paystack = client or get_paystack_client()
    refused: AppError | None = None
    result: TransferResult | None = None
    try:
        result = await _start_or_find_transfer(
            paystack, payout.amount_minor, recipient.recipient_code, payout.reference, payout.reason
        )
    except AppError as exc:
        if exc.code != "paystack_refused":
            raise
        refused = exc

    before = audit.snapshot(payout)
    if result is None:
        assert refused is not None
        payout.status = "failed"
        payout.failure_reason = refused.message[:500]
    else:
        payout.provider_transfer_code = result.transfer_code or None
        payout.status = result.status
    if payout.status != "pending":
        payout.completed_at = datetime.now(UTC)
    await session.flush()
    await audit.record(
        session, None, "payout.sent", "payout", payout.id, before=before, after=audit.snapshot(payout)
    )
    if payout.status != before["status"]:
        await _payout_changed(session, payout, before["status"], None)
    return payout


async def list_unsent_payouts(
    session: AsyncSession, older_than: datetime, limit: int = 100
) -> list[uuid.UUID]:
    """Pending payouts with no transfer code, last touched before `older_than` (for the sweeper)."""
    rows = await session.scalars(
        select(Payout.id)
        .where(
            Payout.status == "pending",
            Payout.provider_transfer_code.is_(None),
            Payout.updated_at < older_than,
        )
        .order_by(Payout.updated_at)
        .limit(limit)
    )
    return list(rows)


# --- a project's ledger -----------------------------------------------------------------------


async def list_entries_touching(
    session: AsyncSession,
    *,
    account_prefixes: Sequence[str],
    refs: Sequence[tuple[str, uuid.UUID]] = (),
    since: datetime | None = None,
    until: datetime | None = None,
    cursor: str | None = None,
    limit: int = pagination.DEFAULT_LIMIT,
) -> tuple[list[LedgerEntry], str | None]:
    """Every entry of the transactions that touch these accounts or refs, newest first, one page.

    A transaction counts when any of its entries is on an account starting with one of
    `account_prefixes`, or has one of the (ref_type, ref_id) pairs; all of its entries are then
    returned (so a release shows both its escrow and its contractor_payable side).
    `since` is inclusive, `until` exclusive (created_at, UTC). Paginated with core/pagination.py.
    """
    if not 1 <= limit <= pagination.MAX_LIMIT:
        raise AppError("invalid_limit", f"limit must be between 1 and {pagination.MAX_LIMIT}.", 422)
    touching = [LedgerEntry.account.startswith(prefix, autoescape=True) for prefix in account_prefixes]
    touching += [
        (LedgerEntry.ref_type == ref_type) & (LedgerEntry.ref_id == ref_id) for ref_type, ref_id in refs
    ]
    if not touching:
        return [], None
    transactions = select(LedgerEntry.transaction_id).where(or_(*touching))
    query = select(LedgerEntry).where(LedgerEntry.transaction_id.in_(transactions))
    if since is not None:
        query = query.where(LedgerEntry.created_at >= since)
    if until is not None:
        query = query.where(LedgerEntry.created_at < until)
    if cursor is not None:
        at, entry_id = pagination.decode_cursor(cursor)
        query = query.where(tuple_(LedgerEntry.created_at, LedgerEntry.id) < tuple_(at, entry_id))
    rows = list(
        await session.scalars(
            query.order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc()).limit(limit + 1)
        )
    )
    return pagination.page(rows, limit, lambda e: (e.created_at, e.id))
