"""Follow-ups: a Paystack transfer whose answer is lost can be retried; payout_recipients.supplier_id
points at suppliers; payments tables have single check-constraint names. HTTP mocked with respx."""

import uuid
from collections.abc import Iterator

import httpx
import pytest
import respx
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import initiate_transfer
from app.base.payments.models import PayoutRecipient
from app.base.payments.paystack import HttpPaystackClient
from app.base.payments.tests.webhook_helpers import PAYSTACK_SECRET, webhook_secrets
from app.core.errors import AppError
from app.features.escrow.tests.release_helpers import add_recipient
from app.features.projects.tests.factories import make_user

API = "https://api.paystack.co"
REFERENCE = "payout-test-" + "b" * 20


@pytest.fixture(autouse=True)
def _secrets(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with webhook_secrets(monkeypatch):
        yield


@pytest.fixture
def paystack_http() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=API, assert_all_called=False) as router:
        yield router


def http_client() -> HttpPaystackClient:
    return HttpPaystackClient(PAYSTACK_SECRET, API)


def found(status: str = "success", code: str = "TRF_first") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "status": True,
            "message": "Transfer retrieved",
            "data": {"reference": REFERENCE, "transfer_code": code, "status": status},
        },
    )


async def recipient_code(db_session: AsyncSession) -> str:
    contractor = await make_user(db_session, "contractor")
    return (await add_recipient(db_session, user_id=contractor.id)).recipient_code


async def test_lost_answer_then_retry_keeps_the_first_transfer(
    db_session: AsyncSession, paystack_http: respx.MockRouter
) -> None:
    code = await recipient_code(db_session)
    transfer = paystack_http.post("/transfer")
    verify = paystack_http.get(f"/transfer/verify/{REFERENCE}")

    # Try 1: Paystack took the transfer, but the answer never arrived, and it can't confirm yet.
    transfer.mock(side_effect=httpx.ReadTimeout("lost"))
    verify.mock(side_effect=httpx.ConnectTimeout("still down"))
    with pytest.raises(AppError) as err:
        async with db_session.begin_nested():  # the caller's transaction rolls back
            await initiate_transfer(db_session, code, 5_000_000, REFERENCE, reason="Milestone 1")
    assert err.value.code == "paystack_unavailable"

    # Try 2: Paystack refuses the reference it already has; the lookup finds the first transfer.
    transfer.mock(
        return_value=httpx.Response(400, json={"status": False, "message": "Duplicate Transfer Reference"})
    )
    verify.mock(return_value=found())
    payout = await initiate_transfer(db_session, code, 5_000_000, REFERENCE, reason="Milestone 1")

    assert (payout.status, payout.provider_transfer_code) == ("success", "TRF_first")
    assert transfer.call_count == 2  # never a third, never a second payment


async def test_lost_answer_found_by_the_lookup_at_once(
    db_session: AsyncSession, paystack_http: respx.MockRouter
) -> None:
    code = await recipient_code(db_session)
    paystack_http.post("/transfer").mock(side_effect=httpx.ReadTimeout("lost"))
    paystack_http.get(f"/transfer/verify/{REFERENCE}").mock(return_value=found("pending", "TRF_slow"))
    payout = await initiate_transfer(db_session, code, 5_000_000, REFERENCE, reason="Milestone 1")
    assert (payout.status, payout.provider_transfer_code) == ("pending", "TRF_slow")


async def test_real_refusal_is_still_refused(
    db_session: AsyncSession, paystack_http: respx.MockRouter
) -> None:
    code = await recipient_code(db_session)
    paystack_http.post("/transfer").respond(400, json={"status": False, "message": "Insufficient balance"})
    paystack_http.get(f"/transfer/verify/{REFERENCE}").respond(
        404, json={"status": False, "message": "Transfer not found"}
    )
    with pytest.raises(AppError) as err:
        await initiate_transfer(db_session, code, 5_000_000, REFERENCE, reason="Milestone 1")
    assert (err.value.code, err.value.message) == ("paystack_refused", "Insufficient balance")


async def test_recipient_supplier_must_exist(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="fk_payout_recipients_supplier_id_suppliers"):
        async with db_session.begin_nested():
            db_session.add(
                PayoutRecipient(
                    supplier_id=uuid.uuid4(),
                    provider="paystack",
                    recipient_code=f"RCP_{uuid.uuid4().hex[:12]}",
                    bank_code="058",
                    bank_name="GTBank",
                    account_name="Nobody",
                    account_number_masked="******0000",
                    currency="NGN",
                )
            )


async def test_payments_tables_have_single_check_constraint_names(db_session: AsyncSession) -> None:
    rows = await db_session.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE contype = 'c' AND conrelid::regclass::text IN "
            "('ledger_entries', 'payment_events', 'escrow_accounts', 'escrow_holds', 'escrow_releases', "
            "'payout_recipients', 'payouts')"
        )
    )
    names = [name for (name,) in rows]
    assert "ck_payouts_amount_positive" in names
    assert [n for n in names if n.count("ck_") > 1] == []
