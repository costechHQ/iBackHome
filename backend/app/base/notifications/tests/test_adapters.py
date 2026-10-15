"""Each channel adapter against a fake provider: what it sends, and that failures raise SendError."""

import json
import smtplib
from collections.abc import Callable, Iterator
from email.message import EmailMessage
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.base.notifications import adapters as adapters_module
from app.base.notifications.adapters import (
    DevLogAdapter,
    EmailAdapter,
    FcmPushAdapter,
    SendError,
    TermiiSmsAdapter,
    get_adapters,
)
from app.base.notifications.models import Channel
from app.base.notifications.settings import NotificationSettings, get_notification_settings
from app.base.notifications.templates import Rendered

DEVICE = "device-token-1"  # a test push token, not a secret
MESSAGE = Rendered(
    template="milestone.claimed", text="Foundation is done.", title="Claimed", subject="Claimed"
)

Handler = Callable[[httpx.Request], httpx.Response]


def settings(**overrides: Any) -> NotificationSettings:
    return NotificationSettings(_env_file=None, **overrides)  # type: ignore[call-arg]


# --- SMS (Termii) ------------------------------------------------------------------------------


async def test_termii_sends_plain_sms() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.ng.termii.com/api/sms/send"
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"message_id": "9122821270554876574", "message": "Successfully Sent"})

    adapter = TermiiSmsAdapter(settings(termii_api_key="key-123"), transport=httpx.MockTransport(handler))
    assert await adapter.send("+2348031234567", MESSAGE) == "9122821270554876574"
    assert seen == [
        {
            "api_key": "key-123",
            "to": "2348031234567",  # no plus sign
            "from": "iBackHome",
            "sms": "Foundation is done.",
            "type": "plain",
            "channel": "generic",
        }
    ]


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(401, json={"message": "invalid api key"}),
        lambda r: httpx.Response(200, json={"message": "no id"}),
    ],
    ids=["refused", "no-message-id"],
)
async def test_termii_failures_raise(handler: Handler) -> None:
    adapter = TermiiSmsAdapter(settings(termii_api_key="k"), transport=httpx.MockTransport(handler))
    with pytest.raises(SendError, match="sms"):
        await adapter.send("+2348031234567", MESSAGE)


async def test_termii_unreachable_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    adapter = TermiiSmsAdapter(settings(termii_api_key="k"), transport=httpx.MockTransport(handler))
    with pytest.raises(SendError, match="ConnectError"):
        await adapter.send("+2348031234567", MESSAGE)


# --- push (FCM) --------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def service_account() -> dict[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    return {
        "client_email": "push@ibackhome-test.iam.gserviceaccount.com",
        "private_key": pem,
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def fcm_settings(account: dict[str, str]) -> NotificationSettings:
    return settings(fcm_project_id="ibackhome-test", fcm_service_account_json=json.dumps(account))


async def test_fcm_signs_in_once_and_sends(service_account: dict[str, str]) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url == "https://oauth2.googleapis.com/token":
            assertion = dict(httpx.QueryParams(request.content.decode()))["assertion"]
            claims = jwt.decode(assertion, options={"verify_signature": False})
            assert claims["scope"] == "https://www.googleapis.com/auth/firebase.messaging"
            assert claims["iss"] == service_account["client_email"]
            return httpx.Response(200, json={"access_token": "ya29.token", "expires_in": 3600})
        assert request.headers["Authorization"] == "Bearer ya29.token"
        body = json.loads(request.content)["message"]
        assert body["token"] == DEVICE
        assert body["notification"] == {"title": "Claimed", "body": "Foundation is done."}
        return httpx.Response(200, json={"name": "projects/ibackhome-test/messages/0:123"})

    adapter = FcmPushAdapter(fcm_settings(service_account), transport=httpx.MockTransport(handler))
    assert await adapter.send("device-token-1", MESSAGE) == "projects/ibackhome-test/messages/0:123"
    await adapter.send("device-token-1", MESSAGE)
    assert calls.count("https://oauth2.googleapis.com/token") == 1  # the access token is reused


async def test_fcm_refused_raises(service_account: dict[str, str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth2" in str(request.url):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return httpx.Response(404, json={"error": {"status": "UNREGISTERED"}})

    adapter = FcmPushAdapter(fcm_settings(service_account), transport=httpx.MockTransport(handler))
    with pytest.raises(SendError, match="404"):
        await adapter.send("old-token", MESSAGE)


async def test_fcm_bad_service_account_raises() -> None:
    adapter = FcmPushAdapter(settings(fcm_project_id="p", fcm_service_account_json="{not json"))
    with pytest.raises(SendError, match="not valid JSON"):
        await adapter.send("device-token-1", MESSAGE)


# --- email (SMTP) ------------------------------------------------------------------------------


class FakeSMTP:
    instances: list["FakeSMTP"] = []
    fail = False

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.started_tls = False
        self.logged_in: tuple[str, str] | None = None
        self.sent: list[EmailMessage] = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.logged_in = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        if FakeSMTP.fail:
            raise smtplib.SMTPRecipientsRefused({})
        self.sent.append(message)


@pytest.fixture
def fake_smtp(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[FakeSMTP]]:
    FakeSMTP.instances, FakeSMTP.fail = [], False
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    yield FakeSMTP


EMAIL_SETTINGS = {
    "email_smtp_host": "smtp.example.com",
    "email_smtp_username": "apikey",
    "email_smtp_password": "secret",
    "email_from": "iBackHome <no-reply@ibackhome.ng>",
}


async def test_email_is_sent_over_starttls(fake_smtp: type[FakeSMTP]) -> None:
    ref = await EmailAdapter(settings(**EMAIL_SETTINGS)).send("ada@example.com", MESSAGE)
    [smtp] = fake_smtp.instances
    assert (smtp.host, smtp.port, smtp.started_tls, smtp.logged_in) == (
        "smtp.example.com",
        587,
        True,
        ("apikey", "secret"),
    )
    [email] = smtp.sent
    assert (email["To"], email["Subject"], email["From"]) == (
        "ada@example.com",
        "Claimed",
        "iBackHome <no-reply@ibackhome.ng>",
    )
    assert email.get_content().strip() == "Foundation is done."
    assert ref == email["Message-ID"]


async def test_email_refused_raises(fake_smtp: type[FakeSMTP]) -> None:
    fake_smtp.fail = True
    with pytest.raises(SendError, match="email"):
        await EmailAdapter(settings(**EMAIL_SETTINGS)).send("ada@example.com", MESSAGE)


# --- local log and which adapters are on -------------------------------------------------------


async def test_dev_log_works_only_locally(caplog: pytest.LogCaptureFixture) -> None:
    assert await DevLogAdapter(Channel.SMS, "local").send("+2348031234567", MESSAGE) == "dev-log"
    assert "Foundation is done." in caplog.text
    with pytest.raises(SendError, match="not configured"):
        await DevLogAdapter(Channel.SMS, "staging").send("+2348031234567", MESSAGE)


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[str, dict[str, str]], None]]:
    def set_env(name: str, variables: dict[str, str]) -> None:
        monkeypatch.setattr(adapters_module, "get_settings", lambda: type("S", (), {"environment": name})())
        for key in (
            "EMAIL_SMTP_HOST",
            "EMAIL_FROM",
            "TERMII_API_KEY",
            "FCM_PROJECT_ID",
            "FCM_SERVICE_ACCOUNT_JSON",
        ):
            monkeypatch.delenv(key, raising=False)
        for key, value in variables.items():
            monkeypatch.setenv(key, value)
        monkeypatch.chdir("/")  # no .env file is read
        get_notification_settings.cache_clear()

    yield set_env
    get_notification_settings.cache_clear()


def test_nothing_configured_outside_local(environment: Callable[[str, dict[str, str]], None]) -> None:
    environment("production", {})
    assert dict(get_adapters()) == {}


def test_configured_channels_get_real_adapters(environment: Callable[[str, dict[str, str]], None]) -> None:
    environment(
        "staging",
        {
            "EMAIL_SMTP_HOST": "smtp.example.com",
            "EMAIL_FROM": "no-reply@ibackhome.ng",
            "TERMII_API_KEY": "k",
            "FCM_PROJECT_ID": "p",
            "FCM_SERVICE_ACCOUNT_JSON": "{}",
        },
    )
    found = get_adapters()
    assert isinstance(found[Channel.EMAIL], EmailAdapter)
    assert isinstance(found[Channel.SMS], TermiiSmsAdapter)
    assert isinstance(found[Channel.PUSH], FcmPushAdapter)
    assert Channel.WHATSAPP not in found  # WhatsApp adapter is backend day 5


def test_local_logs_every_unconfigured_channel(environment: Callable[[str, dict[str, str]], None]) -> None:
    environment("local", {"TERMII_API_KEY": "k"})
    found = get_adapters()
    assert isinstance(found[Channel.SMS], TermiiSmsAdapter)
    assert all(isinstance(found[c], DevLogAdapter) for c in (Channel.WHATSAPP, Channel.PUSH, Channel.EMAIL))
