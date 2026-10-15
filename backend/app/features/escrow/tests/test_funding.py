"""Funding a milestone: POST /projects/{id}/funding, then Stripe's checkout.session.completed.

Day 3 "done when": a Stripe test payment moves a milestone to funded with balanced entries.
"""

import uuid
from collections import defaultdict
from collections.abc import AsyncIterator, Iterator
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import accounts, balance
from app.base.payments.stripe_checkout import get_checkout_gateway
from app.base.payments.tests.webhook_helpers import webhook_secrets
from app.features.escrow.models import EscrowAccount
from app.features.escrow.tests.factories import (
    FOUNDATION_NGN,
    FakeCheckout,
    Funded,
    completed_event,
    entries_for,
    funding_settings,
    make_active_project,
    payment_event,
    project_entries,
    send_stripe,
    simulated_escrow,
)
from app.features.milestones.models import Milestone, MilestoneStatus
from app.features.projects.tests.factories import audit_entries, bearer, make_project, make_user

# ₦1,500,000.00 at ₦2,000/£ = £750.00; fee 2.5% = £18.75; client pays £768.75.
NET_GBP = 75_000
FEE_GBP = 1_875
TOTAL_GBP = 76_875


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with webhook_secrets(monkeypatch):
        yield from funding_settings(monkeypatch)


@pytest.fixture(autouse=True)
def _fresh_escrow() -> Iterator[None]:
    simulated_escrow().reset()
    yield
    simulated_escrow().reset()


@pytest.fixture
async def gateway(client: AsyncClient) -> AsyncIterator[FakeCheckout]:
    from app.main import app

    fake = FakeCheckout()
    app.dependency_overrides[get_checkout_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_checkout_gateway, None)


@pytest.fixture
async def world(db_session: AsyncSession) -> Funded:
    return await make_active_project(db_session)


async def status_of(session: AsyncSession, milestone: Milestone) -> MilestoneStatus:
    """The milestone's status as the database has it now."""
    await session.refresh(milestone)
    return milestone.status


def funding_url(project_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/funding"


async def start_funding(
    client: AsyncClient, world: Funded, *, currency: str = "GBP", key: str | None = None
) -> dict[str, object]:
    headers = bearer(world.client) | ({"Idempotency-Key": key} if key else {})
    response = await client.post(
        funding_url(world.project.id),
        json={"milestone_id": str(world.foundation.id), "currency": currency},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def pay(client: AsyncClient, gateway: FakeCheckout, world: Funded) -> dict[str, object]:
    """The full happy path: funding endpoint, then Stripe's signed completion webhook."""
    checkout = await start_funding(client, world)
    event = completed_event(gateway.requests[-1], str(checkout["checkout_session_id"]))
    response = await send_stripe(client, event)
    assert response.status_code == 200, response.text
    return event


# --- POST /projects/{id}/funding ------------------------------------------------------------


async def test_client_gets_a_checkout_for_a_pending_milestone(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    body = await start_funding(client, world, key="fund-1")

    assert body["amount_ngn_minor"] == FOUNDATION_NGN
    assert (body["net_minor"], body["fee_minor"], body["total_minor"]) == (NET_GBP, FEE_GBP, TOTAL_GBP)
    assert (body["currency"], body["fx_rate"], body["fee_bps"]) == ("GBP", "2000", 250)
    assert str(body["checkout_url"]).startswith("https://checkout.stripe.com/")

    [sent] = gateway.requests
    assert sent.currency == "GBP" and sent.amount_total_minor == TOTAL_GBP
    assert sent.idempotency_key == f"funding:{world.foundation.id}:fund-1"
    assert sent.metadata == sent.metadata | {
        "project_id": str(world.project.id),
        "milestone_id": str(world.foundation.id),
        "fx_rate": "2000",
        "amount_ngn_minor": str(FOUNDATION_NGN),
        "fee_minor": str(FEE_GBP),
    }
    assert str(world.project.id) in sent.success_url and "{CHECKOUT_SESSION_ID}" in sent.success_url

    # Money only counts when Stripe confirms: nothing in the ledger, milestone still pending.
    assert await project_entries(db_session, world.project.id) == []
    assert world.foundation.status == MilestoneStatus.PENDING
    [audit] = [
        e for e in await audit_entries(db_session, world.foundation.id) if e.action.startswith("funding")
    ]
    assert audit.action == "funding.checkout_created" and audit.actor_id == world.client.id


async def test_same_idempotency_key_returns_the_same_checkout_and_calls_stripe_once(
    client: AsyncClient, gateway: FakeCheckout, world: Funded
) -> None:
    first = await start_funding(client, world, key="same-key")
    second = await start_funding(client, world, key="same-key")

    assert first == second
    assert len(gateway.requests) == 1


async def test_usd_uses_the_usd_rate(client: AsyncClient, gateway: FakeCheckout, world: Funded) -> None:
    body = await start_funding(client, world, currency="USD")

    # 150,000,000 / 1550 = 96,774.19... cents -> 96,775 (rounded up)
    assert (body["net_minor"], body["fx_rate"]) == (96_775, "1550")


async def test_funding_a_milestone_that_is_not_pending_is_refused(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    world.foundation.status = MilestoneStatus.FUNDED
    await db_session.flush()

    response = await client.post(
        funding_url(world.project.id),
        json={"milestone_id": str(world.foundation.id), "currency": "GBP"},
        headers=bearer(world.client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "milestone_not_pending"
    assert gateway.requests == []


async def test_funding_another_projects_milestone_is_refused(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    other = await make_active_project(db_session)

    response = await client.post(
        funding_url(world.project.id),
        json={"milestone_id": str(other.foundation.id), "currency": "GBP"},
        headers=bearer(world.client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "milestone_not_in_project"
    assert gateway.requests == []


@pytest.mark.parametrize(
    ("who", "status", "code"),
    [
        ("contractor", 403, "forbidden_role"),
        ("ops", 403, "forbidden_role"),
        ("other_client", 403, "not_project_member"),
    ],
)
async def test_only_the_projects_client_can_fund(
    client: AsyncClient,
    db_session: AsyncSession,
    gateway: FakeCheckout,
    world: Funded,
    who: str,
    status: int,
    code: str,
) -> None:
    user = {
        "contractor": world.contractor,
        "ops": await make_user(db_session, "ops"),
        "other_client": await make_user(db_session, "client"),
    }[who]

    response = await client.post(
        funding_url(world.project.id),
        json={"milestone_id": str(world.foundation.id), "currency": "GBP"},
        headers=bearer(user),
    )

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert gateway.requests == []


async def test_funding_needs_an_active_project(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    world.project.status = "paused"
    await db_session.flush()

    response = await client.post(
        funding_url(world.project.id),
        json={"milestone_id": str(world.foundation.id), "currency": "GBP"},
        headers=bearer(world.client),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "project_not_active"


async def test_draft_project_with_no_milestones_is_refused(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout
) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)

    response = await client.post(
        funding_url(project.id),
        json={"milestone_id": str(uuid.uuid4()), "currency": "GBP"},
        headers=bearer(owner),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "project_not_active"


@pytest.mark.parametrize("currency", ["JPY", "NGN", "gbp"])
async def test_unsupported_currency_is_refused(
    client: AsyncClient, gateway: FakeCheckout, world: Funded, currency: str
) -> None:
    response = await client.post(
        funding_url(world.project.id),
        json={"milestone_id": str(world.foundation.id), "currency": currency},
        headers=bearer(world.client),
    )

    assert response.status_code == 422
    assert gateway.requests == []


async def test_funding_needs_a_login(client: AsyncClient, gateway: FakeCheckout, world: Funded) -> None:
    response = await client.post(
        funding_url(world.project.id), json={"milestone_id": str(world.foundation.id), "currency": "GBP"}
    )
    assert response.status_code == 401


# --- checkout.session.completed ---------------------------------------------------------------


async def test_paid_checkout_funds_the_milestone_with_balanced_entries(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    event = await pay(client, gateway, world)

    assert await status_of(db_session, world.foundation) == MilestoneStatus.FUNDED
    assert world.foundation.funded_at is not None

    stored = await payment_event(db_session, str(event["id"]))
    assert stored is not None and stored.processed_at is not None
    entries = await entries_for(db_session, stored.id)

    # Every transaction balances, in one currency.
    by_txn: dict[uuid.UUID, list[int]] = defaultdict(lambda: [0, 0])
    currencies: dict[uuid.UUID, set[str]] = defaultdict(set)
    for entry in entries:
        by_txn[entry.transaction_id][0 if entry.direction == "debit" else 1] += entry.amount_minor
        currencies[entry.transaction_id].add(entry.currency)
    assert len(by_txn) == 3
    assert all(debits == credits for debits, credits in by_txn.values())
    assert all(len(c) == 1 for c in currencies.values())

    # Exactly the spec's rows (T1 with the fee as its own entry, T2, T3).
    p = world.project.id
    rows = sorted((e.account, e.direction, e.amount_minor, e.fx_rate) for e in entries)
    assert rows == sorted(
        [
            ("stripe_clearing:GBP", "debit", TOTAL_GBP, None),
            (f"client_funding:{p}:GBP", "credit", NET_GBP, None),
            ("fees:GBP", "credit", FEE_GBP, None),
            (f"client_funding:{p}:GBP", "debit", NET_GBP, Decimal("2000")),
            ("fx_conversion:GBP", "credit", NET_GBP, Decimal("2000")),
            (f"escrow:{p}:NGN", "debit", FOUNDATION_NGN, Decimal("2000")),
            ("fx_conversion:NGN", "credit", FOUNDATION_NGN, Decimal("2000")),
        ]
    )

    # Balances afterwards: escrow holds exactly the naira amount; nothing left in client_funding.
    assert await balance(db_session, accounts.escrow(p, "NGN")) == FOUNDATION_NGN
    assert await balance(db_session, accounts.client_funding(p, "GBP")) == 0
    account = await db_session.scalar(select(EscrowAccount).where(EscrowAccount.project_id == p))
    assert account is not None and account.balance_minor == FOUNDATION_NGN
    held = await simulated_escrow().balance(p)
    assert (held.held_minor, held.currency) == (FOUNDATION_NGN, "NGN")

    actions = [e.action for e in await audit_entries(db_session, world.foundation.id)]
    assert actions == ["funding.checkout_created", "milestone.funded", "escrow.funded"]
    funded_audit = (await audit_entries(db_session, world.foundation.id))[-1]
    assert funded_audit.actor_id is None  # the system, on Stripe's word
    assert funded_audit.after is not None and funded_audit.after["fx_rate"] == "2000"


async def test_same_webhook_twice_funds_once(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    event = await pay(client, gateway, world)

    again = await send_stripe(client, event)

    assert again.status_code == 200 and again.json()["duplicate"] is True
    stored = await payment_event(db_session, str(event["id"]))
    assert stored is not None
    assert len(await entries_for(db_session, stored.id)) == 7
    assert len(await project_entries(db_session, world.project.id)) == 3  # 2x client_funding, 1x escrow
    assert (await simulated_escrow().balance(world.project.id)).held_minor == FOUNDATION_NGN
    actions = [e.action for e in await audit_entries(db_session, world.foundation.id)]
    assert actions.count("milestone.funded") == 1 and actions.count("escrow.funded") == 1


async def test_escrow_hold_failure_commits_nothing_and_the_retry_succeeds(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    checkout = await start_funding(client, world)
    event = completed_event(gateway.requests[-1], str(checkout["checkout_session_id"]))
    simulated_escrow().fail_next("hold")

    failed = await send_stripe(client, event)

    assert failed.status_code == 502  # Stripe retries
    assert failed.json()["error"]["code"] == "escrow_provider_unavailable"
    assert await payment_event(db_session, str(event["id"])) is None
    assert await project_entries(db_session, world.project.id) == []
    assert await status_of(db_session, world.foundation) == MilestoneStatus.PENDING
    assert (
        await db_session.scalar(select(EscrowAccount).where(EscrowAccount.project_id == world.project.id))
        is None
    )

    retried = await send_stripe(client, event)

    assert retried.status_code == 200 and retried.json()["duplicate"] is False
    assert await status_of(db_session, world.foundation) == MilestoneStatus.FUNDED
    assert (await simulated_escrow().balance(world.project.id)).held_minor == FOUNDATION_NGN


async def test_second_payment_for_a_funded_milestone_is_recorded_but_not_held(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    # Two checkout tabs: both created while pending, both paid.
    first = await start_funding(client, world)
    first_request = gateway.requests[-1]
    second = await start_funding(client, world)
    second_request = gateway.requests[-1]
    await send_stripe(client, completed_event(first_request, str(first["checkout_session_id"])))

    event = completed_event(second_request, str(second["checkout_session_id"]))
    response = await send_stripe(client, event)

    assert response.status_code == 200
    stored = await payment_event(db_session, str(event["id"]))
    assert stored is not None
    rows = sorted((e.account, e.direction, e.amount_minor) for e in await entries_for(db_session, stored.id))
    assert rows == [
        (f"client_funding:{world.project.id}:GBP", "credit", TOTAL_GBP),
        ("stripe_clearing:GBP", "debit", TOTAL_GBP),
    ]
    assert (await simulated_escrow().balance(world.project.id)).held_minor == FOUNDATION_NGN  # held once
    [unmatched] = [
        e for e in await audit_entries(db_session, world.foundation.id) if e.action == "funding.unmatched"
    ]
    assert unmatched.after is not None and unmatched.after["reason"] == "milestone_funded"


async def test_amount_that_disagrees_with_the_quote_is_not_held(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    checkout = await start_funding(client, world)
    event = completed_event(gateway.requests[-1], str(checkout["checkout_session_id"]), amount_total=100)

    await send_stripe(client, event)

    assert await status_of(db_session, world.foundation) == MilestoneStatus.PENDING
    assert (await simulated_escrow().balance(world.project.id)).held_minor == 0
    [unmatched] = [
        e for e in await audit_entries(db_session, world.foundation.id) if e.action == "funding.unmatched"
    ]
    assert unmatched.after is not None and unmatched.after["reason"] == "amount_mismatch"


async def test_unpaid_checkout_is_stored_but_changes_nothing(
    client: AsyncClient, db_session: AsyncSession, gateway: FakeCheckout, world: Funded
) -> None:
    checkout = await start_funding(client, world)
    request = gateway.requests[-1]
    unpaid = completed_event(request, str(checkout["checkout_session_id"]), payment_status="unpaid")

    response = await send_stripe(client, unpaid)

    assert response.status_code == 200
    assert await project_entries(db_session, world.project.id) == []
    assert await status_of(db_session, world.foundation) == MilestoneStatus.PENDING

    # Bank transfers and similar confirm later with async_payment_succeeded: that one funds.
    later = completed_event(
        request, str(checkout["checkout_session_id"]), event_type="checkout.session.async_payment_succeeded"
    )
    assert (await send_stripe(client, later)).status_code == 200
    assert await status_of(db_session, world.foundation) == MilestoneStatus.FUNDED


async def test_checkout_that_is_not_a_milestone_funding_is_ignored(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_other",
                "payment_status": "paid",
                "amount_total": 500,
                "currency": "gbp",
            }
        },
    }

    response = await send_stripe(client, event)

    assert response.status_code == 200
    stored = await payment_event(db_session, str(event["id"]))
    assert stored is not None and await entries_for(db_session, stored.id) == []
