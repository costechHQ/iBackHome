"""Paystack payouts: recipients (masked account numbers), idempotent transfers, transfer webhooks.

HTTP to Paystack is mocked with respx; nothing reaches the network.
"""

import json
import uuid
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.payments import initiate_transfer, register_payout_recipient
from app.base.payments.models import Payout, PayoutRecipient
from app.base.payments.tests.webhook_helpers import PAYSTACK_SECRET, body, paystack_headers, webhook_secrets
from app.base.users.models import User
from app.core.errors import AppError
from app.features.projects.tests.factories import make_user
from app.features.suppliers.models import Supplier

API = "https://api.paystack.co"
ACCOUNT_NUMBER = "0123456789"
WEBHOOK_URL = "/api/v1/webhooks/paystack"


@pytest.fixture(autouse=True)
def _secrets(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with webhook_secrets(monkeypatch):
        yield


@pytest.fixture
def paystack() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=API, assert_all_called=False) as router:
        yield router


def recipient_ok(code: str) -> httpx.Response:
    return httpx.Response(
        201,
        json={
            "status": True,
            "message": "Transfer recipient created successfully",
            "data": {
                "recipient_code": code,
                "name": "Chidi Okeke",
                "details": {
                    "account_number": ACCOUNT_NUMBER,
                    "account_name": "CHIDI OKEKE",
                    "bank_code": "058",
                    "bank_name": "Guaranty Trust Bank",
                },
            },
        },
    )


def transfer_ok(reference: str, status: str = "pending") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "status": True,
            "message": "Transfer has been queued",
            "data": {
                "reference": reference,
                "transfer_code": "TRF_test123",
                "status": status,
                "amount": 5_000_000,
            },
        },
    )


def new_reference() -> str:
    return f"payout-{uuid.uuid4().hex}"


async def contractor_recipient(
    session: AsyncSession, paystack: respx.MockRouter, *, code: str | None = None
) -> tuple[User, PayoutRecipient]:
    contractor = await make_user(session, "contractor")
    code = code or f"RCP_{uuid.uuid4().hex[:12]}"
    paystack.post("/transferrecipient").mock(return_value=recipient_ok(code))
    recipient = await register_payout_recipient(
        session,
        account_name="Chidi Okeke",
        account_number=ACCOUNT_NUMBER,
        bank_code="058",
        actor_id=contractor.id,
        user_id=contractor.id,
    )
    return contractor, recipient


# --- recipients ------------------------------------------------------------------------------


async def test_recipient_is_created_and_the_account_number_is_stored_masked(
    db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    contractor, recipient = await contractor_recipient(db_session, paystack)

    sent = json.loads(paystack.calls.last.request.content)
    assert sent == {
        "type": "nuban",
        "name": "Chidi Okeke",
        "account_number": ACCOUNT_NUMBER,
        "bank_code": "058",
        "currency": "NGN",
    }
    assert paystack.calls.last.request.headers["Authorization"] == f"Bearer {PAYSTACK_SECRET}"
    assert recipient.user_id == contractor.id and recipient.supplier_id is None
    assert recipient.account_number_masked == "******6789"
    assert (recipient.bank_name, recipient.account_name) == ("Guaranty Trust Bank", "CHIDI OKEKE")

    # The full number is nowhere in our database: not on the row, not in the audit entry.
    stored = {k: str(v) for k, v in vars(recipient).items() if not k.startswith("_")}
    assert all(ACCOUNT_NUMBER not in value for value in stored.values())
    [entry] = list(await db_session.scalars(select(AuditEntry).where(AuditEntry.object_id == recipient.id)))
    assert entry.action == "payout_recipient.created"
    assert ACCOUNT_NUMBER not in json.dumps(entry.after)


async def test_database_refuses_a_full_account_number(db_session: AsyncSession) -> None:
    contractor = await make_user(db_session, "contractor")
    row = PayoutRecipient(
        user_id=contractor.id,
        provider="paystack",
        recipient_code=f"RCP_{uuid.uuid4().hex[:12]}",
        bank_code="058",
        bank_name="Guaranty Trust Bank",
        account_name="CHIDI OKEKE",
        account_number_masked=ACCOUNT_NUMBER,
        currency="NGN",
    )

    with pytest.raises(IntegrityError, match="account_number_masked"):
        async with db_session.begin_nested():
            db_session.add(row)


async def test_registering_the_same_account_twice_returns_the_same_recipient(
    db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    contractor, first = await contractor_recipient(db_session, paystack, code="RCP_same0001")

    again = await register_payout_recipient(
        db_session,
        account_name="Chidi Okeke",
        account_number=ACCOUNT_NUMBER,
        bank_code="058",
        actor_id=contractor.id,
        user_id=contractor.id,
    )

    assert again.id == first.id


async def test_someone_elses_account_is_refused(db_session: AsyncSession, paystack: respx.MockRouter) -> None:
    await contractor_recipient(db_session, paystack, code="RCP_taken0001")
    other = await make_user(db_session, "contractor")

    with pytest.raises(AppError) as error:
        await register_payout_recipient(
            db_session,
            account_name="Chidi Okeke",
            account_number=ACCOUNT_NUMBER,
            bank_code="058",
            actor_id=other.id,
            user_id=other.id,
        )

    assert (error.value.status_code, error.value.code) == (409, "recipient_belongs_to_another")


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"account_number": "12345"}, "invalid_account_number"),
        ({"account_number": "01234567890"}, "invalid_account_number"),
        ({"bank_code": "05 8"}, "invalid_bank_code"),
        ({"user_id": None}, "recipient_owner_required"),
        ({"supplier_id": uuid.uuid4()}, "recipient_owner_required"),
    ],
)
async def test_bad_bank_details_are_refused_before_calling_paystack(
    db_session: AsyncSession, paystack: respx.MockRouter, kwargs: dict[str, Any], code: str
) -> None:
    contractor = await make_user(db_session, "contractor")
    args: dict[str, Any] = {
        "account_name": "Chidi Okeke",
        "account_number": ACCOUNT_NUMBER,
        "bank_code": "058",
        "actor_id": contractor.id,
        "user_id": contractor.id,
    } | kwargs

    with pytest.raises(AppError) as error:
        await register_payout_recipient(db_session, **args)

    assert error.value.code == code
    assert paystack.calls.call_count == 0


async def test_paystack_refusal_is_a_422_with_its_message(
    db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    contractor = await make_user(db_session, "contractor")
    paystack.post("/transferrecipient").mock(
        return_value=httpx.Response(400, json={"status": False, "message": "Account number is invalid"})
    )

    with pytest.raises(AppError) as error:
        await register_payout_recipient(
            db_session,
            account_name="X",
            account_number=ACCOUNT_NUMBER,
            bank_code="058",
            actor_id=contractor.id,
            user_id=contractor.id,
        )

    assert (error.value.status_code, error.value.code, error.value.message) == (
        422,
        "paystack_refused",
        "Account number is invalid",
    )


async def test_paystack_down_is_a_502(db_session: AsyncSession, paystack: respx.MockRouter) -> None:
    contractor = await make_user(db_session, "contractor")
    paystack.post("/transferrecipient").mock(side_effect=httpx.ConnectTimeout("timed out"))

    with pytest.raises(AppError) as error:
        await register_payout_recipient(
            db_session,
            account_name="X",
            account_number=ACCOUNT_NUMBER,
            bank_code="058",
            actor_id=contractor.id,
            user_id=contractor.id,
        )

    assert (error.value.status_code, error.value.code) == (502, "paystack_unavailable")


async def test_supplier_recipient_has_no_user(db_session: AsyncSession, paystack: respx.MockRouter) -> None:
    paystack.post("/transferrecipient").mock(return_value=recipient_ok("RCP_supplier01"))
    supplier = Supplier(name="Enugu Blocks Ltd", verified=True)
    db_session.add(supplier)
    await db_session.flush()
    supplier_id = supplier.id

    recipient = await register_payout_recipient(
        db_session,
        account_name="Enugu Blocks Ltd",
        account_number=ACCOUNT_NUMBER,
        bank_code="058",
        actor_id=None,
        supplier_id=supplier_id,
    )

    assert (recipient.user_id, recipient.supplier_id) == (None, supplier_id)


# --- transfers -------------------------------------------------------------------------------


async def test_transfer_is_started_with_our_reference(
    db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    contractor, recipient = await contractor_recipient(db_session, paystack)
    reference = new_reference()
    route = paystack.post("/transfer").mock(return_value=transfer_ok(reference))

    payout = await initiate_transfer(
        db_session, recipient.recipient_code, 5_000_000, reference, reason="Milestone 1: Foundation"
    )

    assert json.loads(route.calls.last.request.content) == {
        "source": "balance",
        "amount": 5_000_000,
        "currency": "NGN",
        "recipient": recipient.recipient_code,
        "reference": reference,
        "reason": "Milestone 1: Foundation",
    }
    assert (payout.status, payout.provider_transfer_code, payout.amount_minor) == (
        "pending",
        "TRF_test123",
        5_000_000,
    )
    actions = list(
        await db_session.scalars(select(AuditEntry.action).where(AuditEntry.object_id == payout.id))
    )
    assert actions == ["payout.initiated"]


async def test_same_reference_twice_sends_one_transfer(
    db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    _, recipient = await contractor_recipient(db_session, paystack)
    reference = new_reference()
    route = paystack.post("/transfer").mock(return_value=transfer_ok(reference))

    first = await initiate_transfer(db_session, recipient.recipient_code, 5_000_000, reference, reason="M1")
    second = await initiate_transfer(db_session, recipient.recipient_code, 5_000_000, reference, reason="M1")

    assert first.id == second.id
    assert route.call_count == 1
    count = len(list(await db_session.scalars(select(Payout).where(Payout.reference == reference))))
    assert count == 1


async def test_same_reference_with_another_amount_is_refused(
    db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    _, recipient = await contractor_recipient(db_session, paystack)
    reference = new_reference()
    paystack.post("/transfer").mock(return_value=transfer_ok(reference))
    await initiate_transfer(db_session, recipient.recipient_code, 5_000_000, reference, reason="M1")

    with pytest.raises(AppError) as error:
        await initiate_transfer(db_session, recipient.recipient_code, 6_000_000, reference, reason="M1")

    assert (error.value.status_code, error.value.code) == (409, "payout_reference_conflict")


@pytest.mark.parametrize(
    ("amount", "reference", "code"),
    [
        (0, "payout-0123456789abcdef", "invalid_amount"),
        (100, "short", "invalid_reference"),
        (100, "Payout-UPPER-0123456789", "invalid_reference"),
    ],
)
async def test_bad_transfer_input_is_refused_before_calling_paystack(
    db_session: AsyncSession, paystack: respx.MockRouter, amount: int, reference: str, code: str
) -> None:
    _, recipient = await contractor_recipient(db_session, paystack)
    route = paystack.post("/transfer").mock(return_value=transfer_ok(reference))

    with pytest.raises(AppError) as error:
        await initiate_transfer(db_session, recipient.recipient_code, amount, reference, reason="M1")

    assert error.value.code == code
    assert route.call_count == 0


async def test_unknown_recipient_is_404(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await initiate_transfer(db_session, "RCP_nobody", 100, new_reference(), reason="M1")
    assert (error.value.status_code, error.value.code) == (404, "recipient_not_found")


async def test_transfer_that_paystack_refuses_raises(
    db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    _, recipient = await contractor_recipient(db_session, paystack)
    paystack.post("/transfer").mock(
        return_value=httpx.Response(400, json={"status": False, "message": "Your balance is not enough"})
    )
    # Refused, so we look the reference up: Paystack has no such transfer.
    paystack.get(url__regex=r"/transfer/verify/.+").mock(
        return_value=httpx.Response(404, json={"status": False, "message": "Transfer not found"})
    )

    with pytest.raises(AppError) as error:
        await initiate_transfer(db_session, recipient.recipient_code, 5_000_000, new_reference(), reason="M1")

    assert error.value.code == "paystack_refused"  # the caller's transaction rolls the payout row back


# --- transfer webhooks -----------------------------------------------------------------------


def transfer_event(
    event: str, reference: str, *, transfer_id: int = 4242, amount: int = 5_000_000
) -> dict[str, Any]:
    return {
        "event": event,
        "data": {
            "id": transfer_id,
            "amount": amount,
            "currency": "NGN",
            "reference": reference,
            "transfer_code": "TRF_test123",
            "status": event.split(".")[1],
            "gateway_response": "Insufficient funds" if event == "transfer.failed" else None,
        },
    }


async def send(client: AsyncClient, event: dict[str, Any]) -> httpx.Response:
    raw = body(event)
    return await client.post(WEBHOOK_URL, content=raw, headers=paystack_headers(raw))


async def pending_payout(session: AsyncSession, paystack: respx.MockRouter) -> Payout:
    _, recipient = await contractor_recipient(session, paystack)
    reference = new_reference()
    paystack.post("/transfer").mock(return_value=transfer_ok(reference))
    return await initiate_transfer(session, recipient.recipient_code, 5_000_000, reference, reason="M1")


async def payout_actions(session: AsyncSession, payout: Payout) -> list[str]:
    result = await session.scalars(
        select(AuditEntry.action).where(AuditEntry.object_id == payout.id).order_by(AuditEntry.at)
    )
    return list(result)


async def test_transfer_success_marks_the_payout_paid_once(
    client: AsyncClient, db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    payout = await pending_payout(db_session, paystack)
    event = transfer_event("transfer.success", payout.reference)

    first = await send(client, event)
    second = await send(client, event)

    assert (first.json()["duplicate"], second.json()["duplicate"]) == (False, True)
    await db_session.refresh(payout)
    assert payout.status == "success" and payout.completed_at is not None
    assert await payout_actions(db_session, payout) == ["payout.initiated", "payout.success"]


async def test_transfer_failed_records_the_reason(
    client: AsyncClient, db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    payout = await pending_payout(db_session, paystack)

    await send(client, transfer_event("transfer.failed", payout.reference))

    await db_session.refresh(payout)
    assert (payout.status, payout.failure_reason) == ("failed", "Insufficient funds")


async def test_success_then_reversed(
    client: AsyncClient, db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    payout = await pending_payout(db_session, paystack)

    await send(client, transfer_event("transfer.success", payout.reference))
    await send(client, transfer_event("transfer.reversed", payout.reference))
    # A late success under another transfer id is a new event, but it can't undo the reversal.
    await send(client, transfer_event("transfer.success", payout.reference, transfer_id=99))

    await db_session.refresh(payout)
    assert payout.status == "reversed"
    assert await payout_actions(db_session, payout) == [
        "payout.initiated",
        "payout.success",
        "payout.reversed",
    ]


async def test_impossible_move_is_acknowledged_and_ignored(
    client: AsyncClient, db_session: AsyncSession, paystack: respx.MockRouter
) -> None:
    payout = await pending_payout(db_session, paystack)
    await send(client, transfer_event("transfer.failed", payout.reference, transfer_id=1))

    response = await send(client, transfer_event("transfer.success", payout.reference, transfer_id=2))

    assert response.status_code == 200
    await db_session.refresh(payout)
    assert payout.status == "failed"


async def test_transfer_event_for_an_unknown_reference_is_acknowledged(client: AsyncClient) -> None:
    response = await send(client, transfer_event("transfer.success", new_reference()))
    assert response.status_code == 200
