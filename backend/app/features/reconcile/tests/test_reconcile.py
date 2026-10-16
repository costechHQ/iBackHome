"""Nightly reconciliation (service.py, sources.py, tasks.py). Ledger entries are real (needs Postgres);
the providers are fakes, so no test ever talks to Stripe or Paystack."""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.service import search
from app.base.payments import accounts, credit, debit, post_transaction, record_event
from app.features.escrow.tests.factories import FOUNDATION_NGN, make_active_project
from app.features.escrow.tests.release_helpers import hold_milestone
from app.features.reconcile import service, sources
from app.features.reconcile.sources import EscrowHolding, ProviderTotal, SourceUnavailable
from app.workers.celery_app import celery_app

TODAY = datetime.now(UTC).date()  # ledger rows get the transaction's time, i.e. today (UTC)


class FakeStripe:
    def __init__(self, **paid: tuple[int, int]) -> None:
        self.result = {c: ProviderTotal(c, amount, count) for c, (amount, count) in paid.items()}

    async def paid(self, since: datetime, until: datetime) -> dict[str, ProviderTotal]:
        return self.result


class FakePaystack:
    def __init__(self, **sent: tuple[int, int]) -> None:
        self.result = {c: ProviderTotal(c, amount, count) for c, (amount, count) in sent.items()}

    async def transfers(self, since: datetime, until: datetime) -> dict[str, ProviderTotal]:
        return self.result


class FakeEscrow:
    def __init__(self, *holdings: EscrowHolding) -> None:
        self.result = list(holdings)

    async def holdings(self) -> list[EscrowHolding]:
        return self.result


class Down:
    """A provider that can't be reached."""

    async def paid(self, *_: Any) -> dict[str, ProviderTotal]:
        raise SourceUnavailable("Stripe answered 503")

    async def transfers(self, *_: Any) -> dict[str, ProviderTotal]:
        raise SourceUnavailable("Paystack answered 503")

    async def holdings(self) -> list[EscrowHolding]:
        raise SourceUnavailable("escrow down")


async def stripe_payment(session: AsyncSession, amount_minor: int, currency: str = "GBP") -> uuid.UUID:
    """What Gabriel's funding writes when Stripe confirms a payment (the received leg)."""
    project_id = uuid.uuid4()
    await post_transaction(
        session,
        [
            debit(accounts.stripe_clearing(currency), amount_minor, currency),
            credit(accounts.client_funding(project_id, currency), amount_minor, currency),
        ],
        ref_type="payment_event",
        ref_id=uuid.uuid4(),
    )
    return project_id


async def escrow_hold(session: AsyncSession, project_id: uuid.UUID, amount_minor: int) -> None:
    await post_transaction(
        session,
        [
            debit(accounts.escrow(project_id, "NGN"), amount_minor, "NGN"),
            credit(accounts.fx_conversion("NGN"), amount_minor, "NGN"),
        ],
        ref_type="payment_event",
        ref_id=uuid.uuid4(),
    )


async def run(session: AsyncSession, stripe: Any, paystack: Any, escrow: Any) -> service.ReconcileResult:
    return await service.reconcile_day(session, TODAY, stripe, paystack, escrow)


async def actions(session: AsyncSession, run_id: uuid.UUID) -> list[str]:
    entries, _ = await search(session, object_id=run_id)
    return sorted(e.action for e in entries)


# The comparisons


async def test_matching_data_reports_zero_differences(db_session: AsyncSession) -> None:
    project_id = await stripe_payment(db_session, 150_000)
    await escrow_hold(db_session, project_id, 9_000_000)

    result = await run(
        db_session,
        FakeStripe(GBP=(150_000, 1)),
        FakePaystack(),
        FakeEscrow(EscrowHolding(project_id, "NGN", 9_000_000)),
    )

    assert result.differences == [] and result.ok
    assert result.checked == ["stripe", "paystack", "escrow"]
    assert await actions(db_session, result.run_id) == ["reconcile.completed"]


async def test_amount_mismatch_is_recorded_and_alerted(
    db_session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    await stripe_payment(db_session, 150_000)

    result = await run(db_session, FakeStripe(GBP=(170_000, 1)), FakePaystack(), FakeEscrow())

    [difference] = result.differences
    assert (difference.source, difference.currency, difference.gap_minor) == ("stripe", "GBP", 20_000)
    assert not result.ok
    assert await actions(db_session, result.run_id) == ["reconcile.completed", "reconcile.mismatch"]
    assert any(r.levelname == "ERROR" and "mismatch" in r.getMessage() for r in caplog.records)


async def test_payment_missing_from_the_ledger_is_caught(db_session: AsyncSession) -> None:
    result = await run(db_session, FakeStripe(USD=(25_000, 1)), FakePaystack(), FakeEscrow())

    assert [(d.currency, d.ours_minor, d.theirs_minor) for d in result.differences] == [("USD", 0, 25_000)]


async def test_ledger_entry_stripe_never_reported_is_caught(db_session: AsyncSession) -> None:
    await stripe_payment(db_session, 80_000, "EUR")

    result = await run(db_session, FakeStripe(), FakePaystack(), FakeEscrow())

    assert [(d.currency, d.ours_minor, d.theirs_minor) for d in result.differences] == [("EUR", 80_000, 0)]


async def test_same_total_but_different_count_is_still_a_difference(db_session: AsyncSession) -> None:
    await stripe_payment(db_session, 50_000)
    await stripe_payment(db_session, 50_000)

    result = await run(db_session, FakeStripe(GBP=(100_000, 1)), FakePaystack(), FakeEscrow())

    assert [(d.ours_count, d.theirs_count) for d in result.differences] == [(2, 1)]


async def test_other_days_are_not_counted(db_session: AsyncSession) -> None:
    await stripe_payment(db_session, 150_000)

    result = await service.reconcile_day(
        db_session, TODAY - timedelta(days=1), FakeStripe(), FakePaystack(), FakeEscrow()
    )

    assert result.differences == []


async def test_payout_without_a_ledger_record_is_caught(db_session: AsyncSession) -> None:
    result = await run(db_session, FakeStripe(), FakePaystack(NGN=(50_000_00, 1)), FakeEscrow())

    assert [(d.source, d.theirs_minor, d.ours_minor) for d in result.differences] == [
        ("paystack", 50_000_00, 0)
    ]


async def test_escrow_holding_that_disagrees_with_the_ledger_is_caught(db_session: AsyncSession) -> None:
    project_id = uuid.uuid4()
    await escrow_hold(db_session, project_id, 9_000_000)

    result = await run(
        db_session, FakeStripe(), FakePaystack(), FakeEscrow(EscrowHolding(project_id, "NGN", 8_500_000))
    )

    [difference] = result.differences
    assert (difference.source, difference.project_id, difference.gap_minor) == (
        "escrow",
        str(project_id),
        -500_000,
    )


async def test_unreachable_providers_are_unchecked_not_matched(db_session: AsyncSession) -> None:
    await stripe_payment(db_session, 150_000)

    result = await run(db_session, Down(), Down(), Down())

    assert result.differences == [] and result.checked == []
    assert set(result.unchecked) == {"stripe", "paystack", "escrow"}
    assert not result.ok  # nothing was actually verified


# Escrow through Gabriel's escrow.partner_balances() (simulated partner: escrow's own records)


async def test_escrow_matches_the_ledger_through_the_escrow_service(db_session: AsyncSession) -> None:
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)

    holdings = await sources.EscrowFromService(db_session).holdings()
    mine = [h for h in holdings if h.project_id == funded.project.id]
    assert mine == [EscrowHolding(funded.project.id, "NGN", FOUNDATION_NGN, "records")]

    result = await run(db_session, FakeStripe(), FakePaystack(), sources.EscrowFromService(db_session))
    assert [d for d in result.differences if d.project_id == str(funded.project.id)] == []
    assert "escrow (records)" in result.checked


async def test_ledger_drifting_from_escrow_records_is_caught(db_session: AsyncSession) -> None:
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)
    await escrow_hold(db_session, funded.project.id, 1_000)  # a ledger entry escrow never recorded

    result = await run(db_session, FakeStripe(), FakePaystack(), sources.EscrowFromService(db_session))
    [difference] = [d for d in result.differences if d.project_id == str(funded.project.id)]
    assert (difference.source, difference.ours_minor, difference.theirs_minor) == (
        "escrow",
        FOUNDATION_NGN + 1_000,
        FOUNDATION_NGN,
    )


async def test_escrow_partner_down_is_unchecked(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.errors import AppError
    from app.features.escrow import service as escrow

    async def down(_: AsyncSession) -> list[Any]:
        raise AppError("escrow_provider_unavailable", "The escrow provider is unavailable.", 502)

    monkeypatch.setattr(escrow, "partner_balances", down)
    result = await run(db_session, FakeStripe(), FakePaystack(), sources.EscrowFromService(db_session))
    assert result.unchecked["escrow"] == "escrow partner: escrow_provider_unavailable"


# A payment near midnight counts on the day it happened at Stripe, not the day its webhook arrived


async def late_webhook_payment(session: AsyncSession, happened: datetime, amount_minor: int) -> None:
    """A Stripe event that happened at `happened`, processed (ledger posted) now."""
    _, event = await record_event(
        session,
        "stripe",
        f"evt_{uuid.uuid4().hex}",
        "checkout.session.completed",
        {"id": "evt", "created": int(happened.timestamp()), "type": "checkout.session.completed"},
    )
    assert event is not None
    await post_transaction(
        session,
        [
            debit(accounts.stripe_clearing("GBP"), amount_minor, "GBP"),
            credit(accounts.client_funding(uuid.uuid4(), "GBP"), amount_minor, "GBP"),
        ],
        ref_type="payment_event",
        ref_id=event.id,
    )


async def test_payment_at_2359_with_late_webhook_counts_once(db_session: AsyncSession) -> None:
    yesterday = TODAY - timedelta(days=1)
    just_before_midnight = service.window(TODAY)[0] - timedelta(seconds=30)
    await late_webhook_payment(db_session, just_before_midnight, 42_000)  # ledger posted today

    on_its_day = await service.reconcile_day(
        db_session, yesterday, FakeStripe(GBP=(42_000, 1)), FakePaystack(), FakeEscrow()
    )
    next_day = await service.reconcile_day(db_session, TODAY, FakeStripe(), FakePaystack(), FakeEscrow())

    assert on_its_day.differences == []  # Stripe says yesterday, and so do we
    assert [d for d in next_day.differences if d.source == "stripe"] == []  # not counted again today


# The read-only provider clients (no network: httpx.MockTransport)


def stripe_page(events: list[dict[str, Any]], has_more: bool) -> dict[str, Any]:
    return {"data": events, "has_more": has_more}


def paid_event(event_id: str, currency: str, amount: int, status: str = "paid") -> dict[str, Any]:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {"object": {"currency": currency, "amount_total": amount, "payment_status": status}},
    }


async def test_stripe_client_pages_events_and_counts_only_paid_ones() -> None:
    pages = [
        stripe_page([paid_event("evt_1", "gbp", 1000)], True),
        stripe_page([paid_event("evt_2", "gbp", 500), paid_event("evt_3", "usd", 700, "unpaid")], False),
    ]
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=pages[len(seen) - 1])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        since = datetime(2026, 10, 14, tzinfo=UTC)
        result = await sources.StripeHttp("sk_test_x", http).paid(since, since + timedelta(days=1))

    assert result == {"GBP": ProviderTotal("GBP", 1500, 2)}
    assert seen[0].url.path == "/v1/events"
    assert seen[0].url.params.get_list("types[]") == list(sources.PAID_EVENTS)
    assert seen[0].url.params["created[gte]"] == str(int(since.timestamp()))
    assert seen[1].url.params["starting_after"] == "evt_1"


async def test_paystack_client_counts_successful_transfers_in_the_window() -> None:
    since = datetime(2026, 10, 14, tzinfo=UTC)
    body = {
        "data": [
            {
                "status": "success",
                "currency": "NGN",
                "amount": 300_000,
                "createdAt": "2026-10-14T10:00:00.000Z",
            },
            {"status": "failed", "currency": "NGN", "amount": 999, "createdAt": "2026-10-14T11:00:00.000Z"},
            {"status": "success", "currency": "NGN", "amount": 777, "createdAt": "2026-10-15T00:00:01.000Z"},
        ],
        "meta": {"pageCount": 1},
    }

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    ) as http:
        result = await sources.PaystackHttp("sk_test_x", "https://api.paystack.test", http).transfers(
            since, since + timedelta(days=1)
        )

    assert result == {"NGN": ProviderTotal("NGN", 300_000, 1)}


@pytest.mark.parametrize("client", ["stripe", "paystack"])
async def test_missing_key_or_provider_error_is_unavailable(client: str) -> None:
    now = datetime.now(UTC)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as http:
        if client == "stripe":
            with pytest.raises(SourceUnavailable):
                await sources.StripeHttp("", http).paid(now, now)
            with pytest.raises(SourceUnavailable):
                await sources.StripeHttp("sk_test_x", http).paid(now, now)
        else:
            with pytest.raises(SourceUnavailable):
                await sources.PaystackHttp("", "https://x", http).transfers(now, now)
            with pytest.raises(SourceUnavailable):
                await sources.PaystackHttp("sk_test_x", "https://x", http).transfers(now, now)


def test_runs_nightly_at_01_utc_which_is_02_lagos() -> None:
    import app.features.reconcile.tasks  # noqa: F401 - registers the schedule

    entry = celery_app.conf.beat_schedule["payments.reconcile"]
    assert entry["task"] == "payments.reconcile"
    assert (entry["schedule"].hour, entry["schedule"].minute) == ({1}, {0})


def test_window_is_one_utc_day() -> None:
    since, until = service.window(date(2026, 10, 14))

    assert (since.isoformat(), until.isoformat()) == (
        "2026-10-14T00:00:00+00:00",
        "2026-10-15T00:00:00+00:00",
    )
