"""Subscription rules (spec: "Subscriptions"). Owner: Christopher.

The supervision fee is iBackHome's own income, paid monthly by the project's client through Stripe
Billing. It is never escrow money.

- The final BoQ approval needs an active subscription (`ensure_can_start`).
- A failed payment, or a subscription that ends, pauses the project at once (system `active` ->
  `paused`: claims, verification, approval, funding and release all need an `active` project). A
  payment resumes it, but only if billing paused it (`paused_by_billing`), never an ops pause.
- Every Stripe event is applied once (payment_events), in the webhook's transaction, and only if it
  is newer than the last one applied to that subscription.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base import payments as ledger
from app.base.notifications import notify
from app.base.payments import accounts
from app.base.payments.models import PaymentEvent
from app.base.payments.stripe_billing import BillingGateway, SubscriptionCheckoutRequest
from app.base.users.models import User
from app.core.errors import AppError
from app.features.projects import service as projects
from app.features.projects.models import Project, ProjectStatus
from app.features.projects.transitions import ActorRole
from app.features.subscriptions import messages
from app.features.subscriptions.models import Subscription, SubscriptionInvoice
from app.features.subscriptions.settings import get_subscription_settings

logger = logging.getLogger(__name__)

PURPOSE = "supervision_subscription"
BLOCKING = frozenset({"active", "past_due"})  # a new checkout would double-charge

_STRIPE_STATUS = {
    "active": "active",
    "trialing": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "canceled": "canceled",
    "incomplete_expired": "canceled",
    "incomplete": "incomplete",
}


# --- reading --------------------------------------------------------------------------------------


async def _get(session: AsyncSession, project_id: uuid.UUID, *, lock: bool = False) -> Subscription | None:
    query = select(Subscription).where(Subscription.project_id == project_id)
    return await session.scalar(query.with_for_update() if lock else query)


async def get_subscription(session: AsyncSession, user: User, project_id: uuid.UUID) -> Subscription:
    """The project's subscription, for a member or ops. 403 not_project_member, 404 no_subscription."""
    await projects.require_project_member(session, user, project_id)
    subscription = await _get(session, project_id)
    if subscription is None:
        raise AppError("no_subscription", "This project has no subscription yet.", 404)
    return subscription


async def ensure_can_start(session: AsyncSession, project_id: uuid.UUID) -> None:
    """409 subscription_required unless the project has an active subscription (or it is switched off)."""
    if not get_subscription_settings().subscription_required:
        return
    subscription = await _get(session, project_id)
    if subscription is None or subscription.status != "active":
        raise AppError(
            "subscription_required",
            "The client must start the monthly supervision subscription before the project can start.",
            409,
        )


# --- the client's routes --------------------------------------------------------------------------


async def _client_project(session: AsyncSession, user: User, project_id: uuid.UUID) -> Project:
    project = await projects.get_project(session, project_id)
    if project.client_id != user.id:
        raise AppError("not_project_client", "Only the project's client can manage its subscription.", 403)
    return project


async def create_checkout(
    session: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    currency: str,
    *,
    gateway: BillingGateway,
    idempotency_key: str | None = None,
    request: Request | None = None,
) -> tuple[Subscription, str, str]:
    """Start (or restart after a cancel) the monthly subscription: returns (row, session id, URL).

    - 404 project_not_found; 403 not_project_client
    - 409 project_completed, subscription_exists (already active or past due); 502 stripe_unavailable
    Writes no ledger entries: only Stripe's signed webhooks make it active. Writes an audit entry.
    """
    project = await _client_project(session, user, project_id)
    if project.status == ProjectStatus.COMPLETED.value:
        raise AppError("project_completed", "A completed project does not need a subscription.", 409)
    subscription = await _get(session, project_id, lock=True)
    if subscription is not None and subscription.status in BLOCKING:
        raise AppError("subscription_exists", "This project already has a subscription.", 409)
    settings = get_subscription_settings()
    amount = settings.price_minor(currency)
    if subscription is None:
        subscription = Subscription(
            project_id=project_id, client_id=user.id, currency=currency, amount_minor=amount
        )
        session.add(subscription)
    else:
        subscription.currency, subscription.amount_minor = currency, amount
        subscription.cancel_at_period_end, subscription.canceled_at = False, None
    await session.flush()

    url_values = {"project_id": project_id, "CHECKOUT_SESSION_ID": "{CHECKOUT_SESSION_ID}"}
    metadata = {"purpose": PURPOSE, "project_id": str(project_id), "client_id": str(user.id)}
    checkout = await gateway.create_subscription_checkout(
        SubscriptionCheckoutRequest(
            currency=currency,
            amount_minor=amount,
            product_name=f"iBackHome supervision: {project.title}",
            metadata=metadata,
            success_url=settings.subscription_success_url.format(**url_values),
            cancel_url=settings.subscription_cancel_url.format(**url_values),
            client_reference_id=str(project_id),
            customer_email=user.email,
            idempotency_key=f"subscription:{project_id}:{idempotency_key}" if idempotency_key else None,
        )
    )
    await audit.record(
        session,
        user.id,
        "subscription.checkout_created",
        "project",
        project_id,
        after={"currency": currency, "amount_minor": amount, "checkout_session_id": checkout.id},
        request=request,
    )
    return subscription, checkout.id, checkout.url


async def cancel(
    session: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    *,
    gateway: BillingGateway,
    request: Request | None = None,
) -> Subscription:
    """Stop renewing at the end of the paid month; the project keeps running until then.

    - 403 not_project_client; 404 no_subscription; 409 subscription_not_active
    """
    await _client_project(session, user, project_id)
    subscription = await _get(session, project_id, lock=True)
    if subscription is None:
        raise AppError("no_subscription", "This project has no subscription yet.", 404)
    if subscription.status != "active" or not subscription.stripe_subscription_id:
        raise AppError("subscription_not_active", "Only an active subscription can be canceled.", 409)
    if not subscription.cancel_at_period_end:
        await gateway.cancel_at_period_end(subscription.stripe_subscription_id)
        subscription.cancel_at_period_end = True
        await session.flush()
        await audit.record(
            session,
            user.id,
            "subscription.cancel_requested",
            "project",
            project_id,
            after={"current_period_end": subscription.current_period_end},
            request=request,
        )
    return subscription


# --- Stripe events --------------------------------------------------------------------------------


def _object(event: PaymentEvent) -> dict[str, Any]:
    return (event.payload.get("data") or {}).get("object") or {}


def _event_time(event: PaymentEvent) -> datetime:
    created = event.payload.get("created")
    return datetime.fromtimestamp(int(created), UTC) if created else datetime.now(UTC)


def _seconds(value: Any) -> datetime | None:
    return datetime.fromtimestamp(int(value), UTC) if value else None


def _project_id(metadata: dict[str, Any]) -> uuid.UUID | None:
    if metadata.get("purpose") != PURPOSE:
        return None
    try:
        return uuid.UUID(str(metadata.get("project_id")))
    except ValueError:
        return None


def _invoice_subscription(invoice: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    """(Stripe subscription id, its metadata) from an invoice, in the older and the newer API shape."""
    details = (
        (invoice.get("parent") or {}).get("subscription_details") or invoice.get("subscription_details") or {}
    )
    subscription_id = details.get("subscription") or invoice.get("subscription")
    return (str(subscription_id) if subscription_id else None), details.get("metadata") or {}


async def _find(
    session: AsyncSession, stripe_subscription_id: str | None, metadata: dict[str, Any]
) -> Subscription | None:
    """Our row for a Stripe subscription: by its id, else by the project in its metadata."""
    if stripe_subscription_id:
        found = await session.scalar(
            select(Subscription)
            .where(Subscription.stripe_subscription_id == stripe_subscription_id)
            .with_for_update()
        )
        if found is not None:
            return found
    project_id = _project_id(metadata)
    if project_id is None:
        return None
    found = await _get(session, project_id, lock=True)
    if found is None:
        return None
    # A new checkout after a cancel brings a new Stripe subscription; a late event of the old one is stale.
    if (
        found.stripe_subscription_id
        and found.stripe_subscription_id != stripe_subscription_id
        and found.status != "canceled"
    ):
        return None
    return found


async def _pause_project(
    session: AsyncSession, subscription: Subscription, request: Request | None, key: str
) -> None:
    project = await projects.get_project(session, subscription.project_id, lock=True)
    if project.status != ProjectStatus.ACTIVE.value:
        return  # not running (draft, ops pause, completed): nothing for billing to stop
    await projects.transition(session, project.id, ProjectStatus.PAUSED, ActorRole.SYSTEM, request=request)
    subscription.paused_by_billing = True
    await notify(
        session, subscription.client_id, messages.SUBSCRIPTION_PAUSED, {"project": project.title}, key=key
    )


async def _resume_project(
    session: AsyncSession, subscription: Subscription, request: Request | None, key: str
) -> None:
    if not subscription.paused_by_billing:
        return
    project = await projects.get_project(session, subscription.project_id, lock=True)
    subscription.paused_by_billing = False
    if project.status == ProjectStatus.PAUSED.value:
        await projects.transition(
            session, project.id, ProjectStatus.ACTIVE, ActorRole.SYSTEM, request=request
        )
        await notify(
            session,
            subscription.client_id,
            messages.SUBSCRIPTION_RESUMED,
            {"project": project.title},
            key=key,
        )


async def _set_status(
    session: AsyncSession,
    subscription: Subscription,
    status: str,
    event: PaymentEvent,
    request: Request | None,
) -> None:
    """Move to `status` (once per change), pausing or resuming the project, and audit it."""
    before = subscription.status
    if before == status:
        return
    subscription.status = status
    now = _event_time(event)
    subscription.past_due_since = now if status == "past_due" else None
    if status == "canceled":
        subscription.canceled_at = now
    await session.flush()
    await audit.record(
        session,
        None,
        f"subscription.{status}",
        "project",
        subscription.project_id,
        before={"status": before},
        after={"status": status, "stripe_event": event.event_id},
        request=request,
    )
    if status in ("past_due", "canceled"):
        await _pause_project(session, subscription, request, f"subscription.paused:{event.event_id}")
    elif status == "active":
        await _resume_project(session, subscription, request, f"subscription.resumed:{event.event_id}")


def _is_stale(subscription: Subscription, event: PaymentEvent) -> bool:
    return subscription.stripe_event_at is not None and _event_time(event) < subscription.stripe_event_at


async def apply_subscription_event(
    session: AsyncSession, event: PaymentEvent, request: Request | None = None
) -> None:
    """customer.subscription.created / updated / deleted: the status, period and cancel flag."""
    obj = _object(event)
    metadata = obj.get("metadata") or {}
    if metadata.get("purpose") != PURPOSE:
        return  # not ours
    subscription = await _find(session, str(obj.get("id") or "") or None, metadata)
    if subscription is None:
        logger.warning("stripe subscription %s matches no project; ignored", obj.get("id"))
        return
    if _is_stale(subscription, event):
        return
    item = ((obj.get("items") or {}).get("data") or [{}])[0]
    period_end = obj.get("current_period_end") or item.get("current_period_end")
    subscription.stripe_subscription_id = str(obj["id"])
    subscription.stripe_customer_id = str(obj.get("customer") or "") or subscription.stripe_customer_id
    subscription.current_period_end = _seconds(period_end) or subscription.current_period_end
    subscription.cancel_at_period_end = bool(obj.get("cancel_at_period_end") or obj.get("cancel_at"))
    subscription.stripe_event_at = _event_time(event)
    if event.event_type == "customer.subscription.deleted":
        status = "canceled"
    else:
        status = _STRIPE_STATUS.get(str(obj.get("status")), subscription.status)
    await _set_status(session, subscription, status, event, request)
    await session.flush()


async def apply_invoice_event(
    session: AsyncSession, event: PaymentEvent, request: Request | None = None
) -> None:
    """invoice.paid: record the income and (re)activate. invoice.payment_failed: past due, pause.

    If the invoice arrives before its subscription's own event, this fails (503) so Stripe retries.
    """
    invoice = _object(event)
    stripe_subscription_id, metadata = _invoice_subscription(invoice)
    if stripe_subscription_id is None and not metadata:
        return  # not a subscription invoice
    if metadata and metadata.get("purpose") != PURPOSE:
        return
    subscription = await _find(session, stripe_subscription_id, metadata)
    if subscription is None:
        raise AppError(
            "subscription_not_ready", "The invoice arrived before its subscription; Stripe will retry.", 503
        )
    stale = _is_stale(subscription, event)
    if stripe_subscription_id and not subscription.stripe_subscription_id:
        subscription.stripe_subscription_id = stripe_subscription_id

    if event.event_type == "invoice.paid":
        await _record_invoice(session, subscription, invoice)
        if not stale:
            subscription.stripe_event_at = _event_time(event)
            await _set_status(session, subscription, "active", event, request)
    elif not stale and subscription.status in ("active", "past_due"):
        # A failed first payment (status incomplete) leaves the project waiting; only a running one lapses.
        subscription.stripe_event_at = _event_time(event)
        await _set_status(session, subscription, "past_due", event, request)
    await session.flush()


async def _record_invoice(session: AsyncSession, subscription: Subscription, invoice: dict[str, Any]) -> None:
    invoice_id = str(invoice.get("id") or "")
    paid = int(invoice.get("amount_paid") or 0)
    if not invoice_id or paid <= 0:
        return  # a free or zero invoice earns nothing
    existing = await session.scalar(
        select(SubscriptionInvoice.id).where(SubscriptionInvoice.stripe_invoice_id == invoice_id)
    )
    if existing is not None:
        return
    currency = str(invoice.get("currency") or subscription.currency).upper()
    line_period = (((invoice.get("lines") or {}).get("data") or [{}])[0]).get("period") or {}
    row = SubscriptionInvoice(
        subscription_id=subscription.id,
        stripe_invoice_id=invoice_id,
        period_start=_seconds(line_period.get("start") or invoice.get("period_start")),
        period_end=_seconds(line_period.get("end") or invoice.get("period_end")),
        amount_minor=paid,
        currency=currency,
    )
    session.add(row)
    await session.flush()
    await ledger.post_transaction(
        session,
        [
            ledger.debit(accounts.stripe_clearing(currency), paid, currency),
            ledger.credit(accounts.subscription_revenue(currency), paid, currency),
        ],
        ref_type="subscription_invoice",
        ref_id=row.id,
    )
    await audit.record(
        session,
        None,
        "subscription.invoice_paid",
        "project",
        subscription.project_id,
        after={"stripe_invoice_id": invoice_id, "amount_minor": paid, "currency": currency},
    )
