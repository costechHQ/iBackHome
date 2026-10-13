"""How a login code reaches the user. Owner: Christopher.

Until backend day 5 swaps in Lilian's notify(), the only sender is a development one that writes
the code to the API log, and only when ENVIRONMENT=local. Every other environment refuses (503),
so staging and production can never fall back to logging codes. Nothing else logs a code.
"""

import logging
from typing import Annotated, Protocol

from fastapi import Depends

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)


class OtpSender(Protocol):
    async def send(self, identifier: str, channel: str, code: str) -> None: ...


class DevLogSender:
    """Logs the code so a developer can read it with `docker compose logs api`. Local only."""

    def __init__(self, environment: str) -> None:
        self.environment = environment

    async def send(self, identifier: str, channel: str, code: str) -> None:
        if self.environment != "local":
            raise AppError(
                "otp_sender_not_configured", "Login codes can't be sent in this environment yet.", 503
            )
        logger.warning("DEVELOPMENT login code for %s (%s): %s", identifier, channel, code)


def get_otp_sender() -> OtpSender:
    return DevLogSender(get_settings().environment)


OtpSenderDep = Annotated[OtpSender, Depends(get_otp_sender)]
