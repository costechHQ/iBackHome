"""The public application form on /supervisors (ADR 0005, slice 1). Owner: James.

submit() saves the application, then queues `supervision.send_application_emails` to run only after the
commit (through payments' after_commit helper, as notices.py does). The row is saved first, so an email
outage never loses an application; the job retries until both emails are out, and each one is sent once.

Rules: phones in any form login accepts become E.164; the guarantors are two different people and are not
the applicant; one pending application per phone and per email (409); a per-IP rate limit (429). There is no
NIN anywhere: ops check the registration number first.
"""

import hashlib
import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications import Template, notify_address
from app.base.notifications.adapters import Adapter
from app.base.notifications.models import Channel
from app.base.payments.after_commit import after_commit
from app.base.users import service as users
from app.core.errors import AppError
from app.features.supervision import messages
from app.features.supervision.models import SupervisorWebApplication, WebApplicationStatus
from app.features.supervision.schemas import WebApplicationIn
from app.features.supervision.settings import get_supervision_settings

log = logging.getLogger(__name__)


def _phone(raw: str) -> str:
    """E.164 for any form login accepts; an email address here is a 422."""
    if "@" in raw:
        raise AppError("invalid_phone", "Enter a phone number, not an email address.", 422)
    return users.normalise_identifier(raw)[0]


def _email(raw: str) -> str:
    if "@" not in raw:
        raise AppError("invalid_email", "Enter a valid email address.", 422)
    return users.normalise_identifier(raw)[0]


async def _enforce_ip_limit(session: AsyncSession, ip: str, now: datetime) -> None:
    settings = get_supervision_settings()
    window = timedelta(minutes=settings.application_limit_window_minutes)
    # One request per IP at a time, so two at once can't both slip under the limit.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"application-ip:{ip}"}
    )
    count, oldest = (
        await session.execute(
            select(func.count(), func.min(SupervisorWebApplication.created_at)).where(
                SupervisorWebApplication.requested_ip == ip,
                SupervisorWebApplication.created_at > now - window,
            )
        )
    ).one()
    if count >= settings.application_limit_per_ip:
        retry_after = max(1, int((oldest + window - now).total_seconds()) + 1)
        raise HTTPException(
            429, "Too many applications from this connection. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )  # fmt: skip


async def submit(session: AsyncSession, payload: WebApplicationIn, ip: str) -> SupervisorWebApplication:
    """Save one application (the caller commits). The 'website' honeypot is handled by the route."""
    phone = _phone(payload.phone)
    email = _email(payload.email)
    g1, g2 = _phone(payload.guarantor_1_phone), _phone(payload.guarantor_2_phone)
    if g1 == g2:
        raise AppError("guarantors_must_differ", "Give two different guarantors.", 422)
    if phone in (g1, g2):
        raise AppError("guarantor_is_applicant", "A guarantor can't be the applicant.", 422)
    relatives = [{"name": r.name, "phone": _phone(r.phone)} for r in payload.relatives]

    now = datetime.now(UTC)
    await _enforce_ip_limit(session, ip, now)
    pending = await session.scalar(
        select(SupervisorWebApplication.id).where(
            SupervisorWebApplication.status == WebApplicationStatus.PENDING.value,
            or_(SupervisorWebApplication.phone == phone, SupervisorWebApplication.email == email),
        )
    )
    if pending is not None:
        raise AppError(
            "application_exists", "We already have an application for this phone number or email.", 409
        )
    row = SupervisorWebApplication(
        full_name=payload.full_name,
        phone=phone,
        email=email,
        state=payload.state,
        city=payload.city,
        registration_body=payload.registration_body,
        registration_no=payload.registration_no,
        years_experience=payload.years_experience,
        guarantor_1_name=payload.guarantor_1_name,
        guarantor_1_phone=g1,
        guarantor_2_name=payload.guarantor_2_name,
        guarantor_2_phone=g2,
        relatives=relatives,
        consented_at=now,
        requested_ip=ip,
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError as exc:  # two requests raced past the check above: the unique index decides
        raise AppError(
            "application_exists", "We already have an application for this phone number or email.", 409
        ) from exc
    after_commit(session, enqueue, row.id)
    return row


def enqueue(application_id: uuid.UUID) -> None:
    """Queue the emails. A queue outage must not break the form: the row is saved, so it only logs."""
    from app.features.supervision.tasks import send_application_emails_task

    try:
        send_application_emails_task.delay(str(application_id))
    except Exception:
        log.exception("could not queue the emails for supervisor application %s", application_id)


def _person(name: str, phone: str) -> str:
    return f"{name}, {phone}"


async def send_emails(
    session: AsyncSession,
    application_id: uuid.UUID,
    *,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> bool:
    """Email ops, then the applicant (each once). Commits after each send so it is never repeated.

    Returns True when both have gone out; False means try again later (a provider is down or email
    isn't configured). Never raises for a provider problem: the application is already saved.
    """
    row = await session.get(SupervisorWebApplication, application_id)
    if row is None:
        return True
    settings = get_supervision_settings()
    if row.ops_emailed_at is None:
        relatives = "; ".join(_person(r["name"], r["phone"]) for r in row.relatives) or "none declared"
        data = {
            "full_name": row.full_name,
            "phone": row.phone,
            "email": row.email,
            "city": row.city,
            "state": row.state,
            "registration_body": row.registration_body,
            "registration_no": row.registration_no,
            "years_experience": row.years_experience,
            "guarantor_1": _person(row.guarantor_1_name, row.guarantor_1_phone),
            "guarantor_2": _person(row.guarantor_2_name, row.guarantor_2_phone),
            "relatives": relatives,
            "application_id": row.id,
            "received": row.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        }
        if await _send(session, settings.ops_notify_email, messages.APPLICATION_RECEIVED_OPS, data, adapters):
            row.ops_emailed_at = datetime.now(UTC)
            await session.commit()
    if row.receipt_sent_at is None:
        first = row.full_name.split()[0]
        if await _send(session, row.email, messages.APPLICATION_RECEIPT, {"first_name": first}, adapters):
            row.receipt_sent_at = datetime.now(UTC)
            await session.commit()
    return row.ops_emailed_at is not None and row.receipt_sent_at is not None


async def _send(
    session: AsyncSession, to: str, template: Template, data: Mapping[str, object],
    adapters: Mapping[Channel, Adapter] | None,
) -> bool:  # fmt: skip
    try:
        await notify_address(session, to, "email", template, data, adapters=adapters)
    except AppError as exc:
        log.warning(
            "%s to %s not sent (%s); will retry",
            template.name,
            hashlib.sha256(to.encode()).hexdigest()[:8],
            exc.code,
        )
        return False
    return True
