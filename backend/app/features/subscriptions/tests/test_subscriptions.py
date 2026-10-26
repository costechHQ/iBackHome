"""The monthly supervision subscription: checkout, Stripe webhooks, the BoQ gate and the lapse rule.

"Done when": a failed payment pauses the project at once, a payment resumes it (but never undoes an
ops pause), the income lands in a balanced ledger entry once, and the final BoQ approval needs an
active subscription.
"""

import itertools
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import accounts, balance
from app.base.payments.models import LedgerEntry
from app.base.payments.stripe_billing import SubscriptionCheckoutRequest, get_billing_gateway
from app.base.payments.stripe_checkout import CheckoutSession
from app.base.payments.tests.webhook_helpers import webhook_secrets
from app.features.escrow.tests.factories import send_stripe
from app.features.projects import service as projects
from app.features.projects.models import BoqApproval, Project
from app.features.projects.tests.factories import audit_entries, bearer, make_project, make_user
from app.features.projects.tests.test_boq import BOQ, _approve, _submit, _team
from app.features.subscriptions import service
from app.features.subscriptions.models import Subscription, SubscriptionInvoice
from app.features.subscriptions.settings import get_subscription_settings

_clock = itertools.count(1_800_000_000, 10)


@dataclass
class FakeBilling:
    """Stands in for Stripe Billing: records each request and returns a predictable session."""

    requests: list[SubscriptionCheckoutRequest] = field(default_factory=list)
    canceled: list[str] = field(default_factory=list)

    async def create_subscription_checkout(self, request: SubscriptionCheckoutRequest) -> CheckoutSession:
        self.requests.append(request)
        session_id = f"cs_test_{uuid.uuid4().hex}"
        return CheckoutSession(id=session_id, url=f"https://checkout.stripe.com/c/pay/{session_id}")

    async def cancel_at_period_end(self, subscription_id: str) -> None:
        self.canceled.append(subscription_id)


@pytest.fixture(autouse=True)
def _required(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with webhook_secrets(monkeypatch):
        monkeypatch.setenv("SUBSCRIPTION_REQUIRED", "true")
        get_subscription_settings.cache_clear()
        yield
    get_subscription_settings.cache_clear()


@pytest.fixture
async def billing(client: AsyncClient) -> AsyncIterator[FakeBilling]:
    from app.main import app

    fake = FakeBilling()
    app.dependency_overrides[get_billing_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_billing_gateway, None)


@dataclass
class World:
    project: Project
    client_id: uuid.UUID
    stripe_id: str


async def running_project(session: AsyncSession, *, status: str = "active") -> tuple[Any, Any, Project]:
    client = await make_user(session, "client")
    contractor = await make_user(session, "contractor")
    project = await make_project(session, client=client, contractor=contractor)
    project.status = status
    await session.flush()
    return client, contractor, project


def event(event_type: str, obj: dict[str, Any], *, created: int | None = None) -> dict[str, Any]:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": event_type,
        "created": created or next(_clock),
        "data": {"object": obj},
    }


def sub_object(project: Project, stripe_id: str, status: str = "active", **extra: Any) -> dict[str, Any]:
    return {
        "id": stripe_id,
        "customer": "cus_test",
        "status": status,
        "current_period_end": 1_900_000_000,
        "metadata": {
            "purpose": "supervision_subscription",
            "project_id": str(project.id),
            "client_id": str(project.client_id),
        },
        **extra,
    }


def invoice_object(stripe_id: str, invoice_id: str, *, paid: int = 4900) -> dict[str, Any]:
    return {
        "id": invoice_id,
        "subscription": stripe_id,
        "amount_paid": paid,
        "currency": "gbp",
        "lines": {"data": [{"period": {"start": 1_800_000_000, "end": 1_802_592_000}}]},
    }


async def start_checkout(client: AsyncClient, user: Any, project: Project, **headers: str) -> Any:
    return await client.post(
        f"/api/v1/projects/{project.id}/subscription",
        json={"currency": "GBP"},
        headers=bearer(user) | headers,
    )


async def subscribed(
    client: AsyncClient, session: AsyncSession, billing: FakeBilling, *, status: str = "active"
) -> World:
    """An `status` project whose client has paid the first month (checkout, then Stripe's events)."""
    user, _, project = await running_project(session, status=status)
    assert (await start_checkout(client, user, project)).status_code == 201
    stripe_id = f"sub_{uuid.uuid4().hex[:12]}"
    created = event("customer.subscription.created", sub_object(project, stripe_id))
    assert (await send_stripe(client, created)).status_code == 200
    return World(project, user.id, stripe_id)


async def row(session: AsyncSession, project: Project) -> Subscription:
    subscription = await session.scalar(select(Subscription).where(Subscription.project_id == project.id))
    assert subscription is not None
    await session.refresh(subscription)
    return subscription


async def project_status(session: AsyncSession, project: Project) -> str:
    await session.refresh(project)
    return project.status


# --- checkout ---------------------------------------------------------------------------------------


async def test_client_starts_checkout_and_nothing_is_active_yet(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    user, _, project = await running_project(db_session)
    response = await start_checkout(client, user, project)
    assert response.status_code == 201
    body = response.json()
    assert body["checkout_url"].startswith("https://checkout.stripe.com/")
    assert (body["currency"], body["amount_minor"]) == ("GBP", 4900)
    request = billing.requests[0]
    assert request.metadata == {
        "purpose": "supervision_subscription",
        "project_id": str(project.id),
        "client_id": str(user.id),
    }
    assert (await row(db_session, project)).status == "incomplete"
    assert "subscription.checkout_created" in [e.action for e in await audit_entries(db_session, project.id)]


async def test_only_the_projects_client_can_start_or_cancel(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    _, contractor, project = await running_project(db_session)
    other_client = await make_user(db_session, "client")
    for user in (contractor, other_client):
        response = await start_checkout(client, user, project)
        assert response.status_code == 403
    assert billing.requests == []
    response = await client.post(
        f"/api/v1/projects/{project.id}/subscription/cancel", headers=bearer(other_client)
    )
    assert response.status_code == 403


async def test_a_second_checkout_while_active_is_409(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    user = await db_session.get(Project, world.project.id)
    assert user is not None
    client_user = await projects_client(db_session, world)
    response = await start_checkout(client, client_user, world.project)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "subscription_exists"


async def projects_client(session: AsyncSession, world: World) -> Any:
    from app.base.users.models import User

    user = await session.get(User, world.client_id)
    assert user is not None
    return user


async def test_checkout_with_the_same_idempotency_key_replays(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    user, _, project = await running_project(db_session)
    first = await start_checkout(client, user, project, **{"Idempotency-Key": "sub-key-1"})
    second = await start_checkout(client, user, project, **{"Idempotency-Key": "sub-key-1"})
    assert first.json() == second.json()
    assert len(billing.requests) == 1


# --- the BoQ gate -------------------------------------------------------------------------------------


async def test_final_boq_approval_needs_an_active_subscription(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    team = await _team(db_session)
    await _submit(client, team)
    await _approve(client, team, team.client)
    await _approve(client, team, team.contractor)
    response = await _approve(client, team, team.ops)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "subscription_required"
    approvals = await db_session.scalar(
        select(func.count()).select_from(BoqApproval).where(BoqApproval.project_id == team.project.id)
    )
    assert approvals == 2
    assert (await projects.get_project(db_session, team.project.id)).status == "boq_review"

    db_session.add(
        Subscription(
            project_id=team.project.id,
            client_id=team.client.id,
            currency="GBP",
            amount_minor=4900,
            status="active",
        )
    )
    await db_session.flush()
    assert (await _approve(client, team, team.ops)).status_code == 200
    assert (await projects.get_project(db_session, team.project.id)).status == "active"
    assert BOQ  # the same BoQ the projects tests use


async def test_a_pending_or_lapsed_subscription_does_not_open_the_gate(db_session: AsyncSession) -> None:
    team = await _team(db_session)
    for status in ("incomplete", "past_due", "canceled"):
        subscription = Subscription(
            project_id=team.project.id,
            client_id=team.client.id,
            currency="GBP",
            amount_minor=4900,
            status=status,
        )
        db_session.add(subscription)
        await db_session.flush()
        with pytest.raises(Exception, match="active subscription|subscription"):
            await service.ensure_can_start(db_session, team.project.id)
        await db_session.delete(subscription)
        await db_session.flush()


async def test_the_gate_can_be_switched_off(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    team = await _team(db_session)
    monkeypatch.setenv("SUBSCRIPTION_REQUIRED", "false")
    get_subscription_settings.cache_clear()
    await service.ensure_can_start(db_session, team.project.id)


# --- Stripe events ------------------------------------------------------------------------------------


async def test_subscription_created_activates_it(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    subscription = await row(db_session, world.project)
    assert subscription.status == "active"
    assert subscription.stripe_subscription_id == world.stripe_id
    assert subscription.current_period_end is not None
    assert await project_status(db_session, world.project) == "active"


async def test_paid_invoice_books_balanced_income_once(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    paid = event("invoice.paid", invoice_object(world.stripe_id, "in_test_1"))
    assert (await send_stripe(client, paid)).status_code == 200
    duplicate = await send_stripe(client, paid)
    assert duplicate.json()["duplicate"] is True
    # Stripe may also re-send the same invoice under a new event id: still one booking.
    again = event("invoice.paid", invoice_object(world.stripe_id, "in_test_1"))
    assert (await send_stripe(client, again)).status_code == 200

    assert await balance(db_session, accounts.subscription_revenue("GBP")) <= -4900  # credit side
    invoices = (
        await db_session.scalars(
            select(SubscriptionInvoice).where(SubscriptionInvoice.stripe_invoice_id == "in_test_1")
        )
    ).all()
    assert len(invoices) == 1
    entries = (
        await db_session.scalars(select(LedgerEntry).where(LedgerEntry.ref_id == invoices[0].id))
    ).all()
    assert sorted((e.account, e.direction, e.amount_minor) for e in entries) == [
        ("stripe_clearing:GBP", "debit", 4900),
        ("subscription_revenue:GBP", "credit", 4900),
    ]


async def test_failed_payment_pauses_the_project_at_once_and_payment_resumes_it(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    failed = event("invoice.payment_failed", invoice_object(world.stripe_id, "in_test_2"))
    assert (await send_stripe(client, failed)).status_code == 200
    subscription = await row(db_session, world.project)
    assert (subscription.status, subscription.paused_by_billing) == ("past_due", True)
    assert subscription.past_due_since is not None
    assert await project_status(db_session, world.project) == "paused"
    actions = [e.action for e in await audit_entries(db_session, world.project.id)]
    assert "subscription.past_due" in actions
    assert "project.paused" in actions

    paid = event("invoice.paid", invoice_object(world.stripe_id, "in_test_2"))
    assert (await send_stripe(client, paid)).status_code == 200
    subscription = await row(db_session, world.project)
    assert (subscription.status, subscription.paused_by_billing) == ("active", False)
    assert subscription.past_due_since is None
    assert await project_status(db_session, world.project) == "active"


async def test_payment_never_undoes_an_ops_pause(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    world.project.status = "paused"  # ops paused it for their own reasons
    await db_session.flush()
    failed = event("invoice.payment_failed", invoice_object(world.stripe_id, "in_test_3"))
    await send_stripe(client, failed)
    paid = event("invoice.paid", invoice_object(world.stripe_id, "in_test_3"))
    await send_stripe(client, paid)
    subscription = await row(db_session, world.project)
    assert (subscription.status, subscription.paused_by_billing) == ("active", False)
    assert await project_status(db_session, world.project) == "paused"


async def test_an_ended_subscription_pauses_the_project(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    ended = event("customer.subscription.deleted", sub_object(world.project, world.stripe_id, "canceled"))
    assert (await send_stripe(client, ended)).status_code == 200
    subscription = await row(db_session, world.project)
    assert (subscription.status, subscription.paused_by_billing) == ("canceled", True)
    assert subscription.canceled_at is not None
    assert await project_status(db_session, world.project) == "paused"


async def test_a_lapse_before_the_project_starts_pauses_nothing(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing, status="boq_review")
    failed = event("invoice.payment_failed", invoice_object(world.stripe_id, "in_test_4"))
    await send_stripe(client, failed)
    subscription = await row(db_session, world.project)
    assert (subscription.status, subscription.paused_by_billing) == ("past_due", False)
    assert await project_status(db_session, world.project) == "boq_review"


async def test_a_late_event_cannot_undo_a_newer_one(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    newer = event("customer.subscription.updated", sub_object(world.project, world.stripe_id, "past_due"))
    await send_stripe(client, newer)
    older = event(
        "customer.subscription.updated",
        sub_object(world.project, world.stripe_id, "active"),
        created=1_700_000_000,
    )
    assert (await send_stripe(client, older)).status_code == 200
    assert (await row(db_session, world.project)).status == "past_due"
    assert await project_status(db_session, world.project) == "paused"


async def test_an_invoice_before_its_subscription_is_retried_by_stripe(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, project = await running_project(db_session)
    orphan = invoice_object("sub_unknown", "in_orphan")
    orphan["parent"] = {
        "subscription_details": {
            "subscription": "sub_unknown",
            "metadata": {"purpose": "supervision_subscription", "project_id": str(uuid.uuid4())},
        }
    }
    response = await send_stripe(client, event("invoice.paid", orphan))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "subscription_not_ready"


async def test_other_stripe_subscriptions_are_ignored(client: AsyncClient) -> None:
    other = {"id": "sub_other", "status": "active", "metadata": {}}
    response = await send_stripe(client, event("customer.subscription.created", other))
    assert response.status_code == 200


async def test_newer_api_invoice_shape_is_understood(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    invoice = invoice_object(world.stripe_id, "in_new_shape")
    invoice.pop("subscription")
    invoice["parent"] = {"subscription_details": {"subscription": world.stripe_id, "metadata": {}}}
    response = await send_stripe(client, event("invoice.paid", invoice))
    assert response.status_code == 200
    stored = await db_session.scalar(
        select(SubscriptionInvoice).where(SubscriptionInvoice.stripe_invoice_id == "in_new_shape")
    )
    assert stored is not None


# --- reading and canceling ------------------------------------------------------------------------------


async def test_members_read_it_and_outsiders_do_not(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    url = f"/api/v1/projects/{world.project.id}/subscription"
    owner = await projects_client(db_session, world)
    body = (await client.get(url, headers=bearer(owner))).json()
    assert (body["status"], body["amount_minor"], body["currency"]) == ("active", 4900, "GBP")
    outsider = await make_user(db_session, "client")
    assert (await client.get(url, headers=bearer(outsider))).status_code == 403
    ops = await make_user(db_session, "ops")
    assert (await client.get(url, headers=bearer(ops))).status_code == 200


async def test_reading_before_any_checkout_is_404(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _, project = await running_project(db_session)
    response = await client.get(f"/api/v1/projects/{project.id}/subscription", headers=bearer(user))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_subscription"


async def test_cancel_stops_renewal_but_keeps_the_project_running(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    world = await subscribed(client, db_session, billing)
    owner = await projects_client(db_session, world)
    url = f"/api/v1/projects/{world.project.id}/subscription/cancel"
    response = await client.post(url, headers=bearer(owner))
    assert response.status_code == 200
    assert response.json()["cancel_at_period_end"] is True
    assert billing.canceled == [world.stripe_id]
    assert await project_status(db_session, world.project) == "active"
    await client.post(url, headers=bearer(owner))  # asking twice does not call Stripe twice
    assert billing.canceled == [world.stripe_id]


async def test_cancel_without_an_active_subscription_is_409(
    client: AsyncClient, db_session: AsyncSession, billing: FakeBilling
) -> None:
    user, _, project = await running_project(db_session)
    await start_checkout(client, user, project)
    response = await client.post(f"/api/v1/projects/{project.id}/subscription/cancel", headers=bearer(user))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "subscription_not_active"
