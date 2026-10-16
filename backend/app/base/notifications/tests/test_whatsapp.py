"""WhatsApp Business Cloud API adapter against a fake Meta: what it sends, and that failures raise."""

import json
from typing import Any

import httpx
import pytest

from app.base.notifications.adapters import SendError, WhatsAppAdapter
from app.base.notifications.settings import NotificationSettings
from app.base.notifications.templates import LOGIN_CODE, Template

TOKEN = "test-token"  # noqa: S105 - not a secret: a fake Meta checks it
NUMBER_ID = "109876543210"

CLAIMED = Template(
    name="test.whatsapp.claimed",
    title="Milestone claimed",
    text="{contractor} says '{milestone}' on {project} is done. {contractor} is waiting.",
    whatsapp_template="milestone_claimed_client",
)
PLAIN = Template(name="test.whatsapp.plain", text="Hello {name}")


def settings(**overrides: Any) -> NotificationSettings:
    values: dict[str, Any] = {"whatsapp_access_token": TOKEN, "whatsapp_phone_number_id": NUMBER_ID}
    return NotificationSettings(_env_file=None, **{**values, **overrides})  # type: ignore[call-arg]


def fake_meta(seen: list[dict[str, Any]], status: int = 200, body: Any = None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == f"https://graph.facebook.com/v23.0/{NUMBER_ID}/messages"
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        seen.append(json.loads(request.content))
        reply = body if body is not None else {"messages": [{"id": "wamid.HBgM123"}]}
        return httpx.Response(status, json=reply)

    return httpx.MockTransport(handler)


async def test_sends_the_approved_template_with_parameters_in_order() -> None:
    seen: list[dict[str, Any]] = []
    adapter = WhatsAppAdapter(settings(), transport=fake_meta(seen))
    message = CLAIMED.render({"contractor": "Obi Builders", "milestone": "Foundation", "project": "Bungalow"})

    assert await adapter.send("+2348031234567", message) == "wamid.HBgM123"
    assert seen == [
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "2348031234567",  # no plus sign
            "type": "template",
            "template": {
                "name": "milestone_claimed_client",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        # each placeholder once, in the order it first appears
                        "parameters": [
                            {"type": "text", "text": "Obi Builders"},
                            {"type": "text", "text": "Foundation"},
                            {"type": "text", "text": "Bungalow"},
                        ],
                    }
                ],
            },
        }
    ]


async def test_login_code_adds_the_copy_code_button() -> None:
    seen: list[dict[str, Any]] = []
    adapter = WhatsAppAdapter(settings(whatsapp_language="en_GB"), transport=fake_meta(seen))
    await adapter.send("+447700900123", LOGIN_CODE.render({"code": "482913"}))

    template = seen[0]["template"]
    assert template["name"] == "login_code"
    assert template["language"] == {"code": "en_GB"}
    assert template["components"] == [
        {"type": "body", "parameters": [{"type": "text", "text": "482913"}]},
        {
            "type": "button",
            "sub_type": "url",
            "index": "0",
            "parameters": [{"type": "text", "text": "482913"}],
        },
    ]


async def test_template_without_a_whatsapp_name_goes_as_text() -> None:
    seen: list[dict[str, Any]] = []
    adapter = WhatsAppAdapter(settings(), transport=fake_meta(seen))
    await adapter.send("+2348031234567", PLAIN.render({"name": "Ada"}))
    assert seen[0]["type"] == "text"
    assert seen[0]["text"] == {"preview_url": False, "body": "Hello Ada"}


async def test_templates_can_be_turned_off_for_test_numbers() -> None:
    seen: list[dict[str, Any]] = []
    adapter = WhatsAppAdapter(settings(whatsapp_use_templates=False), transport=fake_meta(seen))
    message = CLAIMED.render({"contractor": "Obi", "milestone": "Roof", "project": "House"})
    await adapter.send("+2348031234567", message)
    assert seen[0]["type"] == "text"
    assert seen[0]["text"]["body"] == message.text


async def test_meta_refusal_raises_with_its_error_code() -> None:
    # 131047: more than 24 hours since the person last wrote (plain text not allowed).
    refusal = {"error": {"message": "Re-engagement message", "code": 131047}}
    adapter = WhatsAppAdapter(settings(), transport=fake_meta([], status=400, body=refusal))
    with pytest.raises(SendError, match=r"whatsapp: Meta answered 400 \(131047\)"):
        await adapter.send("+2348031234567", PLAIN.render({"name": "Ada"}))


async def test_reply_without_a_message_id_raises() -> None:
    adapter = WhatsAppAdapter(settings(), transport=fake_meta([], body={"messages": []}))
    with pytest.raises(SendError, match="no message id"):
        await adapter.send("+2348031234567", PLAIN.render({"name": "Ada"}))


async def test_unreachable_meta_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    adapter = WhatsAppAdapter(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(SendError, match="whatsapp: ConnectError"):
        await adapter.send("+2348031234567", PLAIN.render({"name": "Ada"}))


def test_button_placeholder_must_exist() -> None:
    with pytest.raises(ValueError, match="not a placeholder"):
        Template(name="test.whatsapp.bad", text="{code}", whatsapp_button_param="otp")
