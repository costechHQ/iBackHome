"""The public application form on /contractors (ADR 0007, phase 1). Owner: Christopher.

submit() saves the application, then queues `contractors.send_application_emails` to run only after the commit
(payments' after_commit helper, as in supervision/applications.py). The row is saved first, so an email outage
never loses an application; the job retries until both emails are out, and each one is sent once.

Rules: phones in any form login accepts become E.164; the two references are different people and
neither is the applicant; one pending application per phone and per email (409); a per-IP rate limit
(429). There is no NIN: ops check the registration and the references first.
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
from app.features.contractors import messages
from app.features.contractors.models import ContractorApplication, ContractorApplicationStatus
from app.features.contractors.schemas import ContractorApplicationIn
from app.features.contractors.settings import get_contractor_settings

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
    settings = get_contractor_settings()
    window = timedelta(minutes=settings.contractor_application_limit_window_minutes)
    # One request per IP at a time, so two at once can't both slip under the limit.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"contractor-application-ip:{ip}"},
    )
    count, oldest = (
        await session.execute(
            select(func.count(), func.min(ContractorApplication.created_at)).where(
                ContractorApplication.requested_ip == ip,
                ContractorApplication.created_at > now - window,
            )
        )
    ).one()
    if count >= settings.contractor_application_limit_per_ip:
        retry_after = max(1, int((oldest + window - now).total_seconds()) + 1)
        raise HTTPException(
            429, "Too many applications from this connection. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )  # fmt: skip


async def submit(session: AsyncSession, payload: ContractorApplicationIn, ip: str) -> ContractorApplication:
    """Save one application (the caller commits). The 'website' honeypot is handled by the route."""
    phone = _phone(payload.phone)
    email = _email(payload.email)
    r1, r2 = _phone(payload.reference_1_phone), _phone(payload.reference_2_phone)
    if r1 == r2:
        raise AppError("references_must_differ", "Give two different references.", 422)
    if phone in (r1, r2):
        raise AppError("reference_is_applicant", "A reference can't be the applicant.", 422)

    now = datetime.now(UTC)
    await _enforce_ip_limit(session, ip, now)
    pending = await session.scalar(
        select(ContractorApplication.id).where(
            ContractorApplication.status == ContractorApplicationStatus.PENDING.value,
            or_(ContractorApplication.phone == phone, ContractorApplication.email == email),
        )
    )
    if pending is not None:
        raise AppError(
            "application_exists", "We already have an application for this phone number or email.", 409
        )
    row = ContractorApplication(
        business_name=payload.business_name,
        contact_name=payload.contact_name,
        phone=phone,
        email=email,
        states_served=payload.states_served,
        specialties=list(payload.specialties),
        years_in_business=payload.years_in_business,
        projects_completed=payload.projects_completed,
        cac_rc_number=payload.cac_rc_number,
        corbon_number=payload.corbon_number,
        reference_1_name=payload.reference_1_name,
        reference_1_phone=r1,
        reference_2_name=payload.reference_2_name,
        reference_2_phone=r2,
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
    after_commit(session, enqueue_intake_emails, row.id)
    return row


def enqueue_intake_emails(application_id: uuid.UUID) -> None:
    """Queue the emails. A queue outage must not break the form: the row is saved, so it only logs."""
    from app.features.contractors.tasks import send_application_emails_task

    try:
        send_application_emails_task.delay(str(application_id))
    except Exception:
        log.exception("could not queue the emails for contractor application %s", application_id)


def enqueue_decision_email(application_id: uuid.UUID) -> None:
    from app.features.contractors.tasks import send_decision_email_task

    try:
        send_decision_email_task.delay(str(application_id))
    except Exception:
        log.exception("could not queue the decision email for contractor application %s", application_id)


def _person(name: str, phone: str) -> str:
    return f"{name}, {phone}"


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


async def send_emails(
    session: AsyncSession,
    application_id: uuid.UUID,
    *,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> bool:
    """Email ops, then the applicant (each once). Commits after each send so it is never repeated.

    Returns True when both have gone out; False means try again later (a provider is down or email isn't
    configured). Never raises for a provider problem: the application is already saved.
    """
    row = await session.get(ContractorApplication, application_id)
    if row is None:
        return True
    if row.ops_emailed_at is None:
        data = {
            "business_name": row.business_name,
            "contact_name": row.contact_name,
            "phone": row.phone,
            "email": row.email,
            "states": ", ".join(row.states_served),
            "specialties": ", ".join(row.specialties),
            "years": row.years_in_business,
            "projects": row.projects_completed,
            "cac": row.cac_rc_number or "not given",
            "corbon": row.corbon_number or "not given",
            "reference_1": _person(row.reference_1_name, row.reference_1_phone),
            "reference_2": _person(row.reference_2_name, row.reference_2_phone),
            "application_id": row.id,
            "received": row.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        }
        ops_to = get_contractor_settings().ops_notify_email
        if await _send(session, ops_to, messages.APPLICATION_RECEIVED_OPS, data, adapters):
            row.ops_emailed_at = datetime.now(UTC)
            await session.commit()
    if row.receipt_sent_at is None:
        data = {"first_name": row.contact_name.split()[0], "business_name": row.business_name}
        if await _send(session, row.email, messages.APPLICATION_RECEIPT, data, adapters):
            row.receipt_sent_at = datetime.now(UTC)
            await session.commit()
    return row.ops_emailed_at is not None and row.receipt_sent_at is not None


async def send_decision_email(
    session: AsyncSession,
    application_id: uuid.UUID,
    *,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> bool:
    """Tell the applicant ops' decision, once. True when sent (or nothing to send); False means retry."""
    row = await session.get(ContractorApplication, application_id)
    if row is None or row.decision_emailed_at is not None:
        return True
    if row.status == ContractorApplicationStatus.APPROVED.value:
        template = messages.APPLICATION_APPROVED
        data: dict[str, object] = {
            "first_name": row.contact_name.split()[0],
            "business_name": row.business_name,
        }
    elif row.status == ContractorApplicationStatus.REJECTED.value:
        template = messages.APPLICATION_REJECTED
        data = {
            "first_name": row.contact_name.split()[0],
            "business_name": row.business_name,
            "reason": row.rejection_reason or "",
        }
    else:
        return True  # still pending: nothing to say yet
    if await _send(session, row.email, template, data, adapters):
        row.decision_emailed_at = datetime.now(UTC)
        await session.commit()
        return True
    return False
