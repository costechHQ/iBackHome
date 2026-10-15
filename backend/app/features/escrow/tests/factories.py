"""Test helpers for funding: an active project with naira milestones, a fake Stripe Checkout,
and the signed checkout.session.completed webhook Stripe would send back."""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments.models import LedgerEntry, PaymentEvent
from app.base.payments.settings import get_payments_settings
from app.base.payments.stripe_checkout import CheckoutRequest, CheckoutSession
from app.base.payments.tests.webhook_helpers import body, stripe_headers
from app.base.users.models import User
from app.features.escrow.providers import SimulatedEscrow, get_escrow_provider
from app.features.milestones import service as milestones
from app.features.milestones.models import Milestone
from app.features.milestones.schemas import MilestoneGroup
from app.features.projects.models import Project
from app.features.projects.tests.factories import make_project, make_user

FOUNDATION_NGN = 150_000_000  # ₦1,500,000.00 in kobo
BLOCKWORK_NGN = 130_000_000


@dataclass
class FakeCheckout:
    """Stands in for Stripe: records each request and returns a predictable session."""

    requests: list[CheckoutRequest] = field(default_factory=list)

    async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSession:
        self.requests.append(request)
        session_id = f"cs_test_{uuid.uuid4().hex}"
        return CheckoutSession(id=session_id, url=f"https://checkout.stripe.com/c/pay/{session_id}")


@dataclass
class Funded:
    client: User
    contractor: User
    project: Project
    foundation: Milestone
    blockwork: Milestone


def funding_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fix the test rate and fee whatever the local .env says: ₦2,000 per £1, 2.5% fee."""
    monkeypatch.setenv("FX_NGN_PER_GBP", "2000")
    monkeypatch.setenv("FX_NGN_PER_USD", "1550")
    monkeypatch.setenv("FUNDING_FEE_BPS", "250")
    monkeypatch.delenv("FX_RATES_AS_OF", raising=False)
    get_payments_settings.cache_clear()
    yield
    get_payments_settings.cache_clear()


def simulated_escrow() -> SimulatedEscrow:
    provider = get_escrow_provider()
    assert isinstance(provider, SimulatedEscrow)
    return provider


async def make_active_project(session: AsyncSession) -> Funded:
    """An active project (as if the BoQ was approved) with two pending naira milestones."""
    client = await make_user(session, "client")
    contractor = await make_user(session, "contractor")
    project = await make_project(session, client=client, contractor=contractor)
    project.status = "active"
    foundation, blockwork = await milestones.create_for_project(
        session,
        project.id,
        [
            MilestoneGroup(name="Foundation", amount_minor=FOUNDATION_NGN),
            MilestoneGroup(name="Blockwork to lintel", amount_minor=BLOCKWORK_NGN),
        ],
        "NGN",
    )
    await session.flush()
    return Funded(client, contractor, project, foundation, blockwork)


def completed_event(
    request: CheckoutRequest,
    session_id: str,
    *,
    event_type: str = "checkout.session.completed",
    payment_status: str = "paid",
    amount_total: int | None = None,
) -> dict[str, Any]:
    """The event Stripe sends once the client has paid for the session `request` created."""
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "object": "event",
        "type": event_type,
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "mode": "payment",
                "payment_status": payment_status,
                "amount_total": request.amount_total_minor if amount_total is None else amount_total,
                "currency": request.currency.lower(),
                "client_reference_id": request.client_reference_id,
                "metadata": request.metadata,
            }
        },
    }


async def send_stripe(client: AsyncClient, event: dict[str, Any]) -> Response:
    raw = body(event)
    return await client.post("/api/v1/webhooks/stripe", content=raw, headers=stripe_headers(raw))


async def payment_event(session: AsyncSession, stripe_event_id: str) -> PaymentEvent | None:
    return await session.scalar(
        select(PaymentEvent).where(
            PaymentEvent.provider == "stripe", PaymentEvent.event_id == stripe_event_id
        )
    )


async def entries_for(session: AsyncSession, ref_id: uuid.UUID) -> list[LedgerEntry]:
    result = await session.scalars(
        select(LedgerEntry)
        .where(LedgerEntry.ref_id == ref_id)
        .order_by(LedgerEntry.created_at, LedgerEntry.id)
    )
    return list(result)


async def project_entries(session: AsyncSession, project_id: uuid.UUID) -> list[LedgerEntry]:
    result = await session.scalars(select(LedgerEntry).where(LedgerEntry.account.contains(str(project_id))))
    return list(result)
