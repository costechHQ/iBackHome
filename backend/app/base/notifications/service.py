"""Sending notifications. Owner: Lilian.

    from app.base.notifications import notify
    from app.features.milestones.messages import MILESTONE_CLAIMED     # each feature's templates

    await notify(session, client.id, MILESTONE_CLAIMED, {"milestone": "Foundation", ...})
    await session.commit()                                              # the caller commits

notify() tries the channels in order (default WhatsApp -> push -> SMS -> email) and stops at the
first one that delivers. A channel is skipped when the user has no address for it (no email, no
push token yet) or it is not configured. It never raises because a provider is down: it saves a
`failed` row instead, which notifications.retry_failed (day 5) picks up. Send after the change
the message is about has been committed, so nobody hears about something that was rolled back.

notify_address() is for login codes: one channel, to a raw phone or email that may have no user
yet. It raises if the code can't be sent (the login must say so) and never stores the data.
"""

import logging
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications.adapters import Adapter, get_adapters
from app.base.notifications.models import DEFAULT_ORDER, Channel, Notification, NotificationStatus
from app.base.notifications.templates import Template
from app.base.users import service as users
from app.base.users.models import User
from app.core.errors import AppError

logger = logging.getLogger(__name__)


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


async def notify(
    session: AsyncSession,
    user_id: uuid.UUID,
    template: Template,
    data: Mapping[str, Any],
    channels: Sequence[str] | None = None,
    *,
    adapters: Mapping[Channel, Adapter] | None = None,
) -> Notification:
    """Send `template` to the user on the first channel that works. Returns the saved row.

    `channels` is the order to try (default WhatsApp -> push -> SMS -> email). To reach someone
    on two channels at once (the spec's "WhatsApp + email"), call notify() once per channel.

    - 404 user_not_found
    - ValueError: a placeholder in the template is missing from `data`, or an unknown channel
    """
    user = await users.get_user(session, user_id)
    if user is None:
        raise AppError("user_not_found", "User not found.", 404)
    message = template.render(data)
    order = _channel_order(channels)
    available = get_adapters() if adapters is None else adapters

    problems: list[str] = []
    for channel in order:
        to = _address(user, channel)
        adapter = available.get(channel)
        if to is None:
            problems.append(f"{channel.value}: no address")
            continue
        if adapter is None:
            problems.append(f"{channel.value}: not configured")
            continue
        try:
            ref = await adapter.send(to, message)
        except Exception as exc:  # noqa: BLE001 - any provider failure means "try the next channel"
            logger.warning("notification %s via %s failed: %s", template.name, channel.value, exc)
            problems.append(f"{channel.value}: {exc}"[:300])
            continue
        row = Notification(
            user_id=user.id,
            channel=channel.value,
            template=template.name,
            payload=jsonable_encoder(dict(data)),
            recipient=to,
            status=NotificationStatus.SENT.value,
            provider_ref=ref[:255] or None,
            attempts=len(problems) + 1,
            error="; ".join(problems) or None,
            sent_at=datetime.now(UTC),
        )
        break
    else:
        logger.warning("notification %s for user %s failed on every channel", template.name, user.id)
        row = Notification(
            user_id=user.id,
            channel=order[-1].value,
            template=template.name,
            payload=jsonable_encoder(dict(data)),
            recipient=None,
            status=NotificationStatus.FAILED.value,
            attempts=len(order),
            error="; ".join(problems),
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
