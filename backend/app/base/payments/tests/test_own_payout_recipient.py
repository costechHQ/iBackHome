"""A contractor's own payout account: banks, account-name lookup, save and read back (masked).

HTTP to Paystack is mocked with respx; nothing reaches the network.
"""

import json
from collections.abc import Iterator

import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.payments.models import PayoutRecipient
from app.base.payments.settings import get_payments_settings
from app.base.payments.tests.webhook_helpers import webhook_secrets
from app.features.agents.service import is_forbidden
from app.features.projects.tests.factories import bearer, make_user

API = "https://api.paystack.co"
ACCOUNT = "0123456789"
URL = "/api/v1/me/payout/recipient"


@pytest.fixture(autouse=True)
def _secrets(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with webhook_secrets(monkeypatch):
        yield


@pytest.fixture
def paystack() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=API, assert_all_called=False) as router:
        yield router


def resolved(name: str = "CHUKWUEMEKA NWOSU") -> httpx.Response:
    return httpx.Response(
        200, json={"status": True, "message": "Account number resolved", "data": {"account_name": name}}
    )


def recipient_created() -> httpx.Response:
    return httpx.Response(
        201,
        json={
            "status": True,
            "message": "Transfer recipient created successfully",
            "data": {
                "recipient_code": "RCP_own_1",
                "name": "CHUKWUEMEKA NWOSU",
                "details": {
                    "account_number": ACCOUNT,
                    "account_name": "CHUKWUEMEKA NWOSU",
                    "bank_code": "011",
                    "bank_name": "First Bank of Nigeria",
                },
            },
        },
    )


async def test_banks_come_sorted_once_each_and_only_active(
    client: AsyncClient, db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    paystack.get("/bank").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": True,
                "data": [
                    {"code": "058", "name": "Guaranty Trust Bank", "active": True},
                    {"code": "011", "name": "First Bank of Nigeria", "active": True},
                    {"code": "011", "name": "First Bank of Nigeria", "active": True},
                    {"code": "999", "name": "Closed Bank", "active": False},
                ],
            },
        )
    )
    contractor = await make_user(db_session, "contractor")
    response = await client.get("/api/v1/banks", headers=bearer(contractor))
    assert response.status_code == 200
    assert response.json() == [
        {"code": "011", "name": "First Bank of Nigeria"},
        {"code": "058", "name": "Guaranty Trust Bank"},
    ]


async def test_the_contractor_checks_whose_name_the_account_is_in(
    client: AsyncClient, db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    lookup = paystack.get("/bank/resolve").mock(return_value=resolved())
    contractor = await make_user(db_session, "contractor")
    response = await client.post(
        f"{URL}/resolve", json={"bank_code": "011", "account_number": ACCOUNT}, headers=bearer(contractor)
    )
    assert response.status_code == 200
    assert response.json() == {"account_name": "CHUKWUEMEKA NWOSU"}
    assert lookup.calls.last.request.url.params["account_number"] == ACCOUNT
    # Nothing saved by a lookup.
    assert (
        await db_session.scalar(select(PayoutRecipient).where(PayoutRecipient.user_id == contractor.id))
        is None
    )


async def test_lookup_problems_are_designed_errors(
    client: AsyncClient, db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    contractor = await make_user(db_session, "contractor")
    headers = bearer(contractor)
    short = await client.post(
        f"{URL}/resolve", json={"bank_code": "011", "account_number": "12345"}, headers=headers
    )
    assert short.status_code == 422

    paystack.get("/bank/resolve").mock(
        return_value=httpx.Response(422, json={"status": False, "message": "Could not resolve account name."})
    )
    refused = await client.post(
        f"{URL}/resolve", json={"bank_code": "011", "account_number": ACCOUNT}, headers=headers
    )
    assert (refused.status_code, refused.json()["error"]["code"]) == (422, "paystack_refused")

    paystack.get("/bank/resolve").mock(return_value=httpx.Response(500))
    down = await client.post(
        f"{URL}/resolve", json={"bank_code": "011", "account_number": ACCOUNT}, headers=headers
    )
    assert (down.status_code, down.json()["error"]["code"]) == (502, "paystack_unavailable")


async def test_save_uses_the_bank_s_name_keeps_the_number_masked_and_is_audited(
    client: AsyncClient, db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    paystack.get("/bank/resolve").mock(return_value=resolved())
    paystack.post("/transferrecipient").mock(return_value=recipient_created())
    contractor = await make_user(db_session, "contractor")
    headers = bearer(contractor)

    assert (await client.get(URL, headers=headers)).json()["error"]["code"] == "no_payout_recipient"
    # The name can't be sent: it is the bank's.
    typed = await client.put(
        URL,
        json={"bank_code": "011", "account_number": ACCOUNT, "account_name": "Someone Else"},
        headers=headers,
    )
    assert typed.status_code == 422

    saved = await client.put(URL, json={"bank_code": "011", "account_number": ACCOUNT}, headers=headers)
    assert saved.status_code == 200
    body = saved.json()
    assert body["account_name"] == "CHUKWUEMEKA NWOSU"
    assert body["account_number_masked"] == "******6789"
    assert body["bank_name"] == "First Bank of Nigeria"
    assert (await client.get(URL, headers=headers)).json()["account_number_masked"] == "******6789"

    # The full number went to Paystack only: not in the row, the response or the audit entry.
    sent = json.loads(paystack.routes[1].calls.last.request.content)
    assert sent["account_number"] == ACCOUNT
    assert ACCOUNT not in json.dumps(body)
    entry = await db_session.scalar(
        select(AuditEntry).where(
            AuditEntry.action == "payout_recipient.created", AuditEntry.actor_id == contractor.id
        )
    )
    assert entry is not None
    assert ACCOUNT not in json.dumps(entry.after)


async def test_only_contractors_and_no_agent_token(client: AsyncClient, db_session: AsyncSession) -> None:
    for role in ("client", "ops", "supervisor"):
        user = await make_user(db_session, role)
        response = await client.get(URL, headers=bearer(user))
        assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden_role")
    assert (await client.get(URL)).status_code == 401
    # "payout" in the path: no agent token can ever list these routes.
    for route in (f"GET {URL}", f"PUT {URL}", f"POST {URL}/resolve"):
        assert is_forbidden(route)


async def test_without_paystack_set_up_it_says_so(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "")
    get_payments_settings.cache_clear()
    contractor = await make_user(db_session, "contractor")
    response = await client.get("/api/v1/banks", headers=bearer(contractor))
    assert (response.status_code, response.json()["error"]["code"]) == (503, "paystack_not_configured")
