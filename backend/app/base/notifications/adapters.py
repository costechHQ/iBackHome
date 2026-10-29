"""How a message reaches a phone or inbox.

Every channel is an adapter with one method:

    async def send(self, to: str, message: Rendered) -> str   # the provider's message id

An adapter raises SendError (or any exception) when the provider refuses or can't be reached;
notify() then tries the next channel. Adapters never touch the database.

- EmailAdapter: SMTP (any provider: Brevo, SES, Gmail...).
- TermiiSmsAdapter: SMS through Termii (spec decision 5 may pick another provider; only this
  class would change).
- FcmPushAdapter: Firebase Cloud Messaging HTTP v1, to one device's push token.
- WhatsAppAdapter: WhatsApp Business Cloud API (Meta). Sends the Meta-approved template when the
  message has one, plain text otherwise.
- DevLogAdapter: writes the message to the API log. Used only on ENVIRONMENT=local, for channels
  that are not configured, so staging and production never fall back to logging.
- FakeAdapter: for tests; records what it sent and can be told to fail.
"""

import asyncio
import json
import logging
import smtplib
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any, Protocol

import httpx
import jwt

from app.base.notifications.models import Channel
from app.base.notifications.settings import NotificationSettings, get_notification_settings
from app.base.notifications.templates import Rendered
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SendError(Exception):
    """The provider refused the message or could not be reached."""


class Adapter(Protocol):
    async def send(self, to: str, message: Rendered) -> str: ...


# --- email (SMTP) ------------------------------------------------------------------------------


class EmailAdapter:
    def __init__(self, settings: NotificationSettings) -> None:
        self.settings = settings

    def _send_blocking(self, to: str, message: Rendered) -> str:
        s = self.settings
        email = EmailMessage()
        email["From"] = s.email_from
        email["To"] = to
        email["Subject"] = message.subject
        email["Message-ID"] = make_msgid(domain="ibackhome")
        email.set_content(message.text)
        with smtplib.SMTP(s.email_smtp_host, s.email_smtp_port, timeout=s.notify_timeout_seconds) as smtp:
            if s.email_smtp_starttls:
                smtp.starttls()
            if s.email_smtp_username:
                smtp.login(s.email_smtp_username, s.email_smtp_password)
            smtp.send_message(email)
        return str(email["Message-ID"])

    async def send(self, to: str, message: Rendered) -> str:
        # smtplib blocks, so it runs in a thread and never stalls the event loop.
        try:
            return await asyncio.to_thread(self._send_blocking, to, message)
        except (smtplib.SMTPException, OSError) as exc:
            raise SendError(f"email: {exc.__class__.__name__}") from exc


# --- SMS (Termii) ------------------------------------------------------------------------------


class TermiiSmsAdapter:
    def __init__(
        self, settings: NotificationSettings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings = settings
        self.transport = transport

    async def send(self, to: str, message: Rendered) -> str:
        s = self.settings
        body = {
            "api_key": s.termii_api_key,
            "to": to.lstrip("+"),  # Termii wants 2348031234567, no plus sign
            "from": s.termii_sender_id,
            "sms": message.text,
            "type": "plain",
            "channel": s.termii_channel,
        }
        async with httpx.AsyncClient(
            base_url=s.termii_base_url, timeout=s.notify_timeout_seconds, transport=self.transport
        ) as client:
            try:
                response = await client.post("/api/sms/send", json=body)
            except httpx.HTTPError as exc:
                raise SendError(f"sms: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            raise SendError(f"sms: Termii answered {response.status_code}")
        message_id = response.json().get("message_id")
        if not message_id:
            raise SendError("sms: Termii gave no message_id")
        return str(message_id)


# --- push (Firebase Cloud Messaging HTTP v1) ---------------------------------------------------

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


class FcmPushAdapter:
    """Sends to one device push token. Signs in to Google with the service account (OAuth 2)."""

    def __init__(
        self, settings: NotificationSettings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings = settings
        self.transport = transport
        self._token: str | None = None
        self._token_expires = 0.0

    def _service_account(self) -> dict[str, Any]:
        try:
            account: dict[str, Any] = json.loads(self.settings.fcm_service_account_json)
        except json.JSONDecodeError as exc:
            raise SendError("push: FCM_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
        return account

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        account = self._service_account()
        now = int(time.time())
        token_uri = account.get("token_uri", "https://oauth2.googleapis.com/token")
        assertion = jwt.encode(
            {
                "iss": account["client_email"],
                "scope": FCM_SCOPE,
                "aud": token_uri,
                "iat": now,
                "exp": now + 3600,
            },
            account["private_key"],
            algorithm="RS256",
        )
        response = await client.post(
            token_uri,
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
        )
        if response.status_code >= 400:
            raise SendError(f"push: Google sign-in answered {response.status_code}")
        data = response.json()
        self._token = str(data["access_token"])
        self._token_expires = now + float(data.get("expires_in", 3600))
        return self._token

    async def send(self, to: str, message: Rendered) -> str:
        url = f"https://fcm.googleapis.com/v1/projects/{self.settings.fcm_project_id}/messages:send"
        async with httpx.AsyncClient(
            timeout=self.settings.notify_timeout_seconds, transport=self.transport
        ) as client:
            try:
                token = await self._access_token(client)
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "message": {
                            "token": to,
                            "notification": {"title": message.title, "body": message.text},
                            "data": {"template": message.template},
                        }
                    },
                )
            except httpx.HTTPError as exc:
                raise SendError(f"push: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            raise SendError(f"push: FCM answered {response.status_code}")
        return str(response.json().get("name", ""))


# --- WhatsApp (Business Cloud API) -------------------------------------------------------------


class WhatsAppAdapter:
    """Sends through Meta's Cloud API from our business number.

    A business may start a conversation only with a template Meta has approved, so a message whose
    template names one goes as that template (its placeholders as the body parameters, plus a
    copy-code button for login codes). Otherwise it goes as plain text, which Meta refuses outside
    the 24 hours after the person last wrote to us; notify() then falls back to the next channel.
    """

    def __init__(
        self, settings: NotificationSettings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings = settings
        self.transport = transport

    def _body(self, to: str, message: Rendered) -> dict[str, Any]:
        s = self.settings
        recipient = to.lstrip("+")  # Meta wants 2348031234567, no plus sign
        if not (s.whatsapp_use_templates and message.whatsapp_template):
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "text",
                "text": {"preview_url": False, "body": message.text},
            }
        components: list[dict[str, Any]] = []
        if message.params:
            components.append(
                {"type": "body", "parameters": [{"type": "text", "text": p} for p in message.params]}
            )
        if message.whatsapp_button is not None:
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": message.whatsapp_button}],
                }
            )
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": {
                "name": message.whatsapp_template,
                "language": {"code": s.whatsapp_language},
                "components": components,
            },
        }

    async def send(self, to: str, message: Rendered) -> str:
        s = self.settings
        path = f"/{s.whatsapp_api_version}/{s.whatsapp_phone_number_id}/messages"
        async with httpx.AsyncClient(
            base_url=s.whatsapp_base_url, timeout=s.notify_timeout_seconds, transport=self.transport
        ) as client:
            try:
                response = await client.post(
                    path,
                    headers={"Authorization": f"Bearer {s.whatsapp_access_token}"},
                    json=self._body(to, message),
                )
            except httpx.HTTPError as exc:
                raise SendError(f"whatsapp: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            code = ""
            try:
                code = str(response.json().get("error", {}).get("code", ""))
            except ValueError:
                pass
            detail = f" ({code})" if code else ""
            raise SendError(f"whatsapp: Meta answered {response.status_code}{detail}")
        try:
            message_id = response.json()["messages"][0]["id"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise SendError("whatsapp: Meta gave no message id") from exc
        return str(message_id)


# --- local development and tests ---------------------------------------------------------------


class DevLogAdapter:
    """Writes the message to the API log. Refuses outside ENVIRONMENT=local."""

    def __init__(self, channel: Channel, environment: str) -> None:
        self.channel = channel
        self.environment = environment

    async def send(self, to: str, message: Rendered) -> str:
        if self.environment != "local":
            raise SendError(f"{self.channel}: not configured")
        logger.warning("DEVELOPMENT %s to %s: %s", self.channel.value, to, message.text)
        return "dev-log"


@dataclass
class FakeAdapter:
    """For tests: remembers every message, or fails when `fail` is set."""

    fail: bool = False
    sent: list[tuple[str, Rendered]] = field(default_factory=list)

    async def send(self, to: str, message: Rendered) -> str:
        if self.fail:
            raise SendError("fake provider is down")
        self.sent.append((to, message))
        return f"fake-{len(self.sent)}"


# --- which adapter serves each channel ---------------------------------------------------------


def get_adapters() -> Mapping[Channel, Adapter]:
    """The adapter for every configured channel (plus the log on ENVIRONMENT=local)."""
    s = get_notification_settings()
    adapters: dict[Channel, Adapter] = {}
    if s.email_smtp_host and s.email_from:
        adapters[Channel.EMAIL] = EmailAdapter(s)
    if s.termii_api_key:
        adapters[Channel.SMS] = TermiiSmsAdapter(s)
    if s.fcm_project_id and s.fcm_service_account_json:
        adapters[Channel.PUSH] = FcmPushAdapter(s)
    if s.whatsapp_access_token and s.whatsapp_phone_number_id:
        adapters[Channel.WHATSAPP] = WhatsAppAdapter(s)
    environment = get_settings().environment
    if environment == "local":
        for channel in Channel:
            adapters.setdefault(channel, DevLogAdapter(channel, environment))
    return adapters
