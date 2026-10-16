"""What the outside world says happened: Stripe, Paystack and the escrow partner. Owner: James.

Read-only clients behind small interfaces, so tests swap in fakes and nothing here can move money.
Gabriel's payment clients only create payments; reconciliation needs to list them, so it has its own.
Keys come from Gabriel's payment settings (STRIPE_SECRET_KEY, PAYSTACK_SECRET_KEY).
"""

import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments.settings import get_payments_settings
from app.core.errors import AppError

STRIPE_API = "https://api.stripe.com/v1"
PAGE = 100


@asynccontextmanager
async def _http(client: httpx.AsyncClient | None) -> AsyncIterator[httpx.AsyncClient]:
    """The injected client as it is (its owner closes it), or a fresh one closed afterwards."""
    if client is not None:
        yield client
        return
    async with httpx.AsyncClient(timeout=30) as fresh:
        yield fresh


class SourceUnavailable(Exception):
    """The provider couldn't be asked (no key, outage, not supported yet). Reported, never guessed."""


@dataclass(frozen=True)
class ProviderTotal:
    currency: str
    amount_minor: int
    count: int


def totals(records: list[tuple[str, int]]) -> dict[str, ProviderTotal]:
    """Sum (currency, amount_minor) records per currency."""
    amounts: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    for currency, amount in records:
        amounts[currency.upper()] += amount
        counts[currency.upper()] += 1
    return {c: ProviderTotal(c, amounts[c], counts[c]) for c in amounts}


# The Stripe events that mean "a Checkout payment is paid" (the ones Gabriel's funding handles).
PAID_EVENTS = ("checkout.session.completed", "checkout.session.async_payment_succeeded")


class StripeSource(Protocol):
    async def paid(self, since: datetime, until: datetime) -> dict[str, ProviderTotal]:
        """Checkout payments that became paid in [since, until) (Stripe event time), per currency."""
        ...


class PaystackSource(Protocol):
    async def transfers(self, since: datetime, until: datetime) -> dict[str, ProviderTotal]:
        """Successful transfers (payouts) created in [since, until), per currency."""
        ...


@dataclass(frozen=True)
class EscrowHolding:
    project_id: uuid.UUID
    currency: str
    available_minor: int  # what the partner says it holds for the project right now
    source: str = "partner"  # "records": the simulated partner, read from escrow's own records


class EscrowSource(Protocol):
    async def holdings(self) -> list[EscrowHolding]: ...


class StripeHttp:
    def __init__(self, secret_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._key = secret_key
        self._client = client

    async def paid(self, since: datetime, until: datetime) -> dict[str, ProviderTotal]:
        """By Stripe event time (when the payment completed), the same clock the ledger side uses
        (payments.provider_event_times), so a payment near midnight is counted on one day only."""
        if not self._key:
            raise SourceUnavailable("STRIPE_SECRET_KEY is not set")
        records: list[tuple[str, int]] = []
        params: dict[str, Any] = {
            "limit": PAGE,
            "types[]": list(PAID_EVENTS),
            "created[gte]": int(since.timestamp()),
            "created[lt]": int(until.timestamp()),
        }
        async with _http(self._client) as http:
            while True:
                response = await http.get(f"{STRIPE_API}/events", params=params, auth=(self._key, ""))
                if response.status_code != 200:
                    raise SourceUnavailable(f"Stripe answered {response.status_code}")
                body = response.json()
                events = body.get("data", [])
                for event in events:
                    checkout = (event.get("data") or {}).get("object") or {}
                    if checkout.get("payment_status") == "paid":
                        records.append((checkout["currency"], int(checkout["amount_total"])))
                if not body.get("has_more") or not events:
                    return totals(records)
                params["starting_after"] = events[-1]["id"]


class PaystackHttp:
    def __init__(self, secret_key: str, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._key = secret_key
        self._base = base_url.rstrip("/")
        self._client = client

    async def transfers(self, since: datetime, until: datetime) -> dict[str, ProviderTotal]:
        if not self._key:
            raise SourceUnavailable("PAYSTACK_SECRET_KEY is not set")
        records: list[tuple[str, int]] = []
        page = 1
        headers = {"Authorization": f"Bearer {self._key}"}
        async with _http(self._client) as http:
            while True:
                params: dict[str, Any] = {
                    "perPage": PAGE,
                    "page": page,
                    "from": since.isoformat(),
                    "to": until.isoformat(),
                }
                response = await http.get(f"{self._base}/transfer", params=params, headers=headers)
                if response.status_code != 200:
                    raise SourceUnavailable(f"Paystack answered {response.status_code}")
                body = response.json()
                rows = body.get("data", [])
                for row in rows:
                    created = datetime.fromisoformat(str(row.get("createdAt", "")).replace("Z", "+00:00"))
                    if row.get("status") == "success" and since <= created < until:
                        records.append((row["currency"], int(row["amount"])))
                meta = body.get("meta") or {}
                if not rows or page >= int(meta.get("pageCount", page)):
                    return totals(records)
                page += 1


class EscrowFromService:
    """What the partner holds, through Gabriel's escrow.partner_balances() (read-only).

    With the simulated partner the figures come from escrow's own hold/release records (its memory
    lives in one process), so they are marked source="records".
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def holdings(self) -> list[EscrowHolding]:
        from app.features.escrow import service as escrow  # escrow imports more than reconcile needs

        try:
            balances = await escrow.partner_balances(self._session)
        except AppError as exc:
            raise SourceUnavailable(f"escrow partner: {exc.code}") from exc
        return [EscrowHolding(b.project_id, b.currency, b.available_minor, b.source) for b in balances]


def default_sources(session: AsyncSession) -> tuple[StripeSource, PaystackSource, EscrowSource]:
    s = get_payments_settings()
    return (
        StripeHttp(s.stripe_secret_key),
        PaystackHttp(s.paystack_secret_key, s.paystack_base_url),
        EscrowFromService(session),
    )
