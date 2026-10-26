"""Database tables for subscriptions (spec: "Subscriptions"). Owner: Christopher.

`subscriptions`: the supervision fee for one project (unique), paid monthly by the project's client
through Stripe Billing. Status: incomplete (checkout started) -> active -> past_due -> active again,
or canceled. `paused_by_billing` is true only when billing paused the project, so a payment never
undoes a pause that ops made. `stripe_event_at` is the time of the last Stripe event applied, so an
event delivered late (Stripe does not guarantee order) cannot undo a newer one.

`subscription_invoices`: each paid Stripe invoice, once (unique `stripe_invoice_id`); the revenue
ledger entries point at it. Change both tables only through service.py.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampedBase


class Subscription(TimestampedBase):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint("currency IN ('GBP', 'USD', 'EUR')", name="currency_supported"),
        CheckConstraint("status IN ('incomplete', 'active', 'past_due', 'canceled')", name="status_valid"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), unique=True, nullable=False
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="incomplete", server_default="incomplete"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    past_due_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_by_billing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SubscriptionInvoice(TimestampedBase):
    __tablename__ = "subscription_invoices"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
        Index("ix_subscription_invoices_subscription_id", "subscription_id"),
    )

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False
    )
    stripe_invoice_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
