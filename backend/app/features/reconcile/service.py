"""Nightly reconciliation: does our ledger agree with Stripe, Paystack and the escrow partner? Owner: James.

Spec: "A nightly reconciliation job compares our ledger with Stripe, Paystack and the escrow partner and
alerts ops on any difference." The person who checks the money isn't the person who wrote the money code,
so this only reads: the ledger through payments.list_entries()/balance(), the providers through sources.py.

What is compared, for one UTC day [day 00:00, next day 00:00):
- Stripe:   completed Checkout payments  vs  ledger debits to stripe_clearing:<CUR> (money received)
- Paystack: successful transfers         vs  ledger entries on escrow_payouts:<CUR> (confirmed payouts)
- Escrow:   what the partner holds       vs  balance(escrow:<project>:<CUR>)        (point in time)
Amounts are integer minor units per currency and are never converted or rounded.

Each difference is written to the audit log ("reconcile.mismatch"; ops find them with
GET /ops/audit?action=reconcile.mismatch) and logged as an error, which the team's Sentry alerts on.
A provider that can't be asked is reported as unchecked, never as matched.
"""

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.payments import accounts, balance, list_entries
from app.features.reconcile.sources import (
    EscrowSource,
    PaystackSource,
    ProviderTotal,
    SourceUnavailable,
    StripeSource,
)

log = logging.getLogger(__name__)

# Currencies clients may pay in (spec: clients abroad) plus naira; Stripe may add others it reports.
STRIPE_CURRENCIES = ("GBP", "USD", "EUR", "NGN")
PAYOUT_CURRENCIES = ("NGN",)
LEDGER_PAGE = 100


@dataclass(frozen=True)
class Difference:
    source: str  # "stripe" | "paystack" | "escrow"
    currency: str
    ours_minor: int  # what our ledger says
    theirs_minor: int  # what the provider says
    ours_count: int | None = None
    theirs_count: int | None = None
    project_id: str | None = None  # escrow differences are per project

    @property
    def gap_minor(self) -> int:
        return self.theirs_minor - self.ours_minor


@dataclass
class ReconcileResult:
    run_id: uuid.UUID
    day: date
    checked: list[str] = field(default_factory=list)  # sources compared
    unchecked: dict[str, str] = field(default_factory=dict)  # source -> why it couldn't be compared
    differences: list[Difference] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.differences and not self.unchecked


def window(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    return start, start + timedelta(days=1)


async def _ledger_sum(
    session: AsyncSession, account: str, since: datetime, until: datetime, *, direction: str | None
) -> tuple[int, int]:
    """(total, count) of an account's entries in the window, optionally one direction only."""
    total, count, cursor = 0, 0, None
    while True:
        page = await list_entries(
            session, account=account, since=since, until=until, cursor=cursor, limit=LEDGER_PAGE
        )
        for entry in page.items:
            if direction is None or entry.direction == direction:
                total += entry.amount_minor
                count += 1
        if page.next_cursor is None:
            return total, count
        cursor = page.next_cursor


def compare_totals(
    source: str, ours: dict[str, tuple[int, int]], theirs: dict[str, ProviderTotal]
) -> list[Difference]:
    """Per-currency differences between our (total, count) and the provider's totals."""
    found = []
    for currency in sorted(set(ours) | set(theirs)):
        our_total, our_count = ours.get(currency, (0, 0))
        their = theirs.get(currency, ProviderTotal(currency, 0, 0))
        if our_total != their.amount_minor or our_count != their.count:
            found.append(Difference(source, currency, our_total, their.amount_minor, our_count, their.count))
    return found


async def reconcile_day(
    session: AsyncSession,
    day: date,
    stripe: StripeSource,
    paystack: PaystackSource,
    escrow: EscrowSource,
) -> ReconcileResult:
    """Compare one UTC day and record the outcome in the audit log. Does not commit."""
    since, until = window(day)
    result = ReconcileResult(run_id=uuid.uuid4(), day=day)

    try:
        theirs = await stripe.paid(since, until)
        ours = {
            c: await _ledger_sum(session, accounts.stripe_clearing(c), since, until, direction="debit")
            for c in sorted(set(STRIPE_CURRENCIES) | set(theirs))
        }
        result.differences += compare_totals("stripe", ours, theirs)
        result.checked.append("stripe")
    except SourceUnavailable as exc:
        result.unchecked["stripe"] = str(exc)

    try:
        theirs = await paystack.transfers(since, until)
        ours = {
            c: await _ledger_sum(session, accounts.escrow_payouts(c), since, until, direction=None)
            for c in sorted(set(PAYOUT_CURRENCIES) | set(theirs))
        }
        result.differences += compare_totals("paystack", ours, theirs)
        result.checked.append("paystack")
    except SourceUnavailable as exc:
        result.unchecked["paystack"] = str(exc)

    try:
        for holding in await escrow.holdings():
            ours_minor = await balance(session, accounts.escrow(holding.project_id, holding.currency))
            if ours_minor != holding.available_minor:
                result.differences.append(
                    Difference(
                        "escrow",
                        holding.currency,
                        ours_minor,
                        holding.available_minor,
                        project_id=str(holding.project_id),
                    )
                )
        result.checked.append("escrow")
    except SourceUnavailable as exc:
        result.unchecked["escrow"] = str(exc)

    await _record(session, result)
    return result


async def _record(session: AsyncSession, result: ReconcileResult) -> None:
    for difference in result.differences:
        details = asdict(difference) | {"gap_minor": difference.gap_minor, "day": result.day.isoformat()}
        log.error("reconciliation mismatch: %s", details)  # error level: Sentry alerts the team
        await audit.record(
            session, None, "reconcile.mismatch", "reconciliation", result.run_id, None, details
        )
    for source, why in result.unchecked.items():
        log.warning("reconciliation: %s not checked (%s)", source, why)
    summary = {
        "day": result.day.isoformat(),
        "checked": result.checked,
        "unchecked": result.unchecked,
        "differences": len(result.differences),
    }
    await audit.record(session, None, "reconcile.completed", "reconciliation", result.run_id, None, summary)
