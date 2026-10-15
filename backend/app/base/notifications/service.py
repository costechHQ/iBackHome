"""Sending notifications.

    from app.base.notifications import notify
    from app.features.milestones.messages import MILESTONE_CLAIMED     # each feature's templates

    await notify(session, client.id, MILESTONE_CLAIMED, {"milestone": "Foundation", ...})
    await session.commit()                                              # the caller commits

notify() tries the channels in order (default WhatsApp -> push -> SMS -> email) and stops at the
first one that delivers. A channel is skipped when the user has no address for it (no email, no
push token yet) or it is not configured. It never raises because a provider is down: it saves a
`failed` row instead, which notifications.retry_failed picks up. Send after the change the
message is about has been committed, so nobody hears about something that was rolled back.

Pass `key` to make a send happen once: a second notify() with the same user, template and key
returns the first row and sends nothing (background jobs can run twice).

notify_address() is for login codes: one channel, to a raw phone or email that may have no user
yet. It raises if the code can't be sent (the login must say so) and never stores the data.
"""

import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications.adapters import Adapter, get_adapters
from app.base.notifications.models import DEFAULT_ORDER, Channel, Notification, NotificationStatus
from app.base.notifications.settings import get_notification_settings
from app.base.notifications.templates import Rendered, Template, get_template
from app.base.users import service as users
from app.base.users.models import User
from app.core.errors import AppError

logger = logging.getLogger(__name__)

KEY_FIELD = "_key"  # where a notify() key is kept inside the saved payload


def _channel_order(channels: Sequence[str] | None) -> list[Channel]:
    if channels is None:
        return list(DEFAULT_ORDER)
    order: list[Channel] = []
    for name in channels:
        channel = Channel(name)  # ValueError on an unknown channel: a programming error
        if channel not in order:
            order.append(channel)
    if not order:
        raise ValueError("channels must name at least one channel")
    return order


def _address(user: User, channel: Channel) -> str | None:
    """Where this user receives this channel, or None if they can't."""
    if channel in (Channel.WHATSAPP, Channel.SMS):
        return user.phone
    if channel == Channel.EMAIL:
        return user.email
    return None  # push: device push tokens are not stored yet


@dataclass
class _Delivery:
    """The outcome of trying channels in order."""

    channel: Channel | None = None  # the one that delivered, if any
    to: str | None = None
    ref: str | None = None
    problems: list[str] = field(default_factory=list)


async def _deliver(
    user: User, message: Rendered, order: Sequence[Channel], available: Mapping[Channel, Adapter]
) -> _Delivery:
    result = _Delivery()
    for channel in order:
        to = _address(user, channel)
        adapter = available.get(channel)
        if to is None:
            result.problems.append(f"{channel.value}: no address")
            continue
        if adapter is None:
            result.problems.append(f"{channel.value}: not configured")
            continue
        try:
            ref = await adapter.send(to, message)
        except Exception as exc:  # noqa: BLE001 - any provider failure means "try the next channel"
            logger.warning("notification %s via %s failed: %s", message.template, channel.value, exc)
            result.problems.append(f"{channel.value}: {exc}"[:300])
            continue
        result.channel, result.to, result.ref = channel, to, ref
        break
    return result


async def _already_sent(
    session: AsyncSession, user_id: uuid.UUID, template: str, key: str
) -> Notification | None:
    return await session.scalar(
        select(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.template == template,
            Notification.payload[KEY_FIELD].astext == key,
        )
        .limit(1)
    )


async def notify(
    session: AsyncSession,
    user_id: uuid.UUID,
    template: Template,
    data: Mapping[str, Any],
    channels: Sequence[str] | None = None,
    *,
    key: str | None = None,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> Notification:
    """Send `template` to the user on the first channel that works. Returns the saved row.

    `channels` is the order to try (default WhatsApp -> push -> SMS -> email). To reach someone
    on two channels at once (the spec's "WhatsApp + email"), call notify() once per channel.
    `key`: a send with the same user, template and key already saved is not repeated.

    - 404 user_not_found
    - ValueError: a placeholder in the template is missing from `data`, or an unknown channel
    """
    user = await users.get_user(session, user_id)
    if user is None:
        raise AppError("user_not_found", "User not found.", 404)
    if key is not None:
        existing = await _already_sent(session, user.id, template.name, key)
        if existing is not None:
            return existing
    message = template.render(data)
    order = _channel_order(channels)
    available = get_adapters() if adapters is None else adapters
    payload = jsonable_encoder(dict(data))
    if key is not None:
        payload[KEY_FIELD] = key

    delivery = await _deliver(user, message, order, available)
    if delivery.channel is not None:
        row = Notification(
            user_id=user.id,
            channel=delivery.channel.value,
            template=template.name,
            payload=payload,
            recipient=delivery.to,
            status=NotificationStatus.SENT.value,
            provider_ref=(delivery.ref or "")[:255] or None,
            attempts=len(delivery.problems) + 1,
            error="; ".join(delivery.problems) or None,
            sent_at=datetime.now(UTC),
        )
    else:
        logger.warning("notification %s for user %s failed on every channel", template.name, user.id)
        row = Notification(
            user_id=user.id,
            channel=order[-1].value,
            template=template.name,
            payload=payload,
            recipient=None,
            status=NotificationStatus.FAILED.value,
            attempts=len(order),
            error="; ".join(delivery.problems),
        )
    session.add(row)
    await session.flush()
    return row


async def notify_address(
    session: AsyncSession,
    identifier: str,
    channel: str,
    template: Template,
    data: Mapping[str, Any],
    *,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> Notification:
    """Send to a raw phone (E.164) or email on exactly this channel. For login codes.

    The data (the code) is used for the message but never stored. Raises:
    - 503 notifications_not_configured: this channel can't send in this environment
    - 502 notification_failed: the provider refused or could not be reached
    - ValueError: unknown channel, or a template placeholder missing from `data`
    """
    chosen = Channel(channel)
    message = template.render(data)
    adapter = (get_adapters() if adapters is None else adapters).get(chosen)
    if adapter is None:
        raise AppError(
            "notifications_not_configured", f"Messages can't be sent by {chosen.value} here yet.", 503
        )
    try:
        ref = await adapter.send(identifier, message)
    except Exception as exc:
        logger.warning("notification %s via %s failed: %s", template.name, chosen.value, exc)
        raise AppError(
            "notification_failed", f"We couldn't send the message by {chosen.value}. Try again.", 502
        ) from exc
    row = Notification(
        user_id=None,
        channel=chosen.value,
        template=template.name,
        payload={},  # never store login codes
        recipient=identifier,
        status=NotificationStatus.SENT.value,
        provider_ref=ref[:255] or None,
        sent_at=datetime.now(UTC),
    )
    session.add(row)
    await session.flush()
    return row


async def retry_failed(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 100,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> dict[str, int]:
    """Try every `failed` row again on all channels (WhatsApp -> push -> SMS -> email).

    Rows older than NOTIFY_RETRY_HOURS, or that have used up NOTIFY_MAX_ATTEMPTS channel tries, are
    left alone. A row whose template is no longer registered, or whose user is gone, is skipped.
    Rows are locked with SKIP LOCKED, so two runs never send the same message twice. The caller
    commits. Returns counts: sent, failed (still), skipped.
    """
    settings = get_notification_settings()
    now = now or datetime.now(UTC)
    rows = list(
        await session.scalars(
            select(Notification)
            .where(
                Notification.status == NotificationStatus.FAILED.value,
                Notification.user_id.is_not(None),
                Notification.created_at >= now - timedelta(hours=settings.notify_retry_hours),
                Notification.attempts < settings.notify_max_attempts,
            )
            .order_by(Notification.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    available = get_adapters() if adapters is None else adapters
    counts = {"sent": 0, "failed": 0, "skipped": 0}
    for row in rows:
        template = get_template(row.template)
        user = await users.get_user(session, row.user_id) if row.user_id else None
        if template is None or user is None:
            counts["skipped"] += 1
            continue
        try:
            message = template.render(row.payload)
        except ValueError:
            counts["skipped"] += 1
            continue
        delivery = await _deliver(user, message, DEFAULT_ORDER, available)
        if delivery.channel is not None:
            row.status = NotificationStatus.SENT.value
            row.channel = delivery.channel.value
            row.recipient = delivery.to
            row.provider_ref = (delivery.ref or "")[:255] or None
            row.sent_at = datetime.now(UTC)
            row.attempts += len(delivery.problems) + 1
            counts["sent"] += 1
        else:
            row.attempts += len(DEFAULT_ORDER)
            counts["failed"] += 1
        row.error = "; ".join(delivery.problems) or None
    await session.flush()
    return counts
