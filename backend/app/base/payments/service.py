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
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import case, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments.models import LedgerEntry
from app.core.errors import AppError

Direction = Literal["debit", "credit"]

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
