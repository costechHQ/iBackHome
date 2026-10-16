"""How a login code reaches the user. Owner: Christopher.

Codes go through Lilian's notifications (`notify_address()` with the LOGIN_CODE template) on exactly
the channel the user chose: SMS (Termii) or WhatsApp for a phone, email for an email.

- A channel that isn't configured answers 503 `notifications_not_configured`; a provider that
  refuses or can't be reached answers 502 `notification_failed`. Either way the request fails,
  nothing is committed and no code is left waiting.
- On ENVIRONMENT=local an unconfigured channel writes the message (with the code) to the API log
  instead, so a developer can read it with `docker compose logs api`. Staging and production never
  log codes. The code itself is never stored: the notifications row keeps only who it went to.
"""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Annotated, Protocol

from fastapi import Depends

from app.core.db import SessionDep

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.base.notifications.adapters import Adapter
    from app.base.notifications.models import Channel


class OtpSender(Protocol):
    async def send(self, identifier: str, channel: str, code: str) -> None: ...


class NotificationSender:
    """Sends the code through notify_address() in the request's own transaction."""

    def __init__(
        self, session: "AsyncSession", *, adapters: "Mapping[Channel, Adapter] | None" = None
    ) -> None:
        self.session = session
        self.adapters = adapters  # tests pass fakes; None = the configured providers

    async def send(self, identifier: str, channel: str, code: str) -> None:
        # Imported here: notifications imports users.service, which imports this module.
        from app.base.notifications import LOGIN_CODE, notify_address

        await notify_address(
            self.session, identifier, channel, LOGIN_CODE, {"code": code}, adapters=self.adapters
        )


def get_otp_sender(session: SessionDep) -> OtpSender:
    return NotificationSender(session)


OtpSenderDep = Annotated[OtpSender, Depends(get_otp_sender)]
