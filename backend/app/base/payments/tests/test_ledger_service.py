"""post_transaction, balance and list_entries: what the Python service accepts and refuses."""

import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.base.payments import accounts, balance, credit, debit, list_entries, post_transaction
from app.base.payments.service import Entry
from app.core.errors import AppError


async def test_balanced_transaction_posts_and_balances(db_session: AsyncSession) -> None:
    project_id, ref_id = uuid.uuid4(), uuid.uuid4()
    clearing, funding = accounts.stripe_clearing("GBP"), accounts.client_funding(project_id, "GBP")

    txn = await post_transaction(
        db_session,
        [debit(clearing, 100_000, "GBP"), credit(funding, 100_000, "GBP")],
        ref_type="payment_event",
        ref_id=ref_id,
    )

    assert isinstance(txn, uuid.UUID)
    assert await balance(db_session, funding) == -100_000
    page = await list_entries(db_session, ref_type="payment_event", ref_id=ref_id)
    assert page.next_cursor is None
    assert {(e.account, e.direction, e.amount_minor, e.currency) for e in page.items} == {
        (clearing, "debit", 100_000, "GBP"),
        (funding, "credit", 100_000, "GBP"),
    }
    assert all(e.transaction_id == txn for e in page.items)


async def test_worked_example_client_pays_1000_gbp(db_session: AsyncSession) -> None:
    """The spec's T1-T3: £1,000 received, converted out, ₦ equivalent held in escrow."""
    project_id, event_id = uuid.uuid4(), uuid.uuid4()
    rate = Decimal("2050.5000000000")  # NGN per GBP
    gbp, ngn = 100_000, 205_050_000  # £1,000.00 and ₦2,050,500.00 in minor units
    assert ngn == int(Decimal(gbp) * rate)

    funding = accounts.client_funding(project_id, "GBP")
    escrow = accounts.escrow(project_id, "NGN")
    common: dict[str, Any] = {"ref_type": "payment_event", "ref_id": event_id}
    await post_transaction(
        db_session,
        [debit(accounts.stripe_clearing("GBP"), gbp, "GBP"), credit(funding, gbp, "GBP")],
        **common,
    )
    await post_transaction(
        db_session, [debit(funding, gbp, "GBP"), credit(accounts.fx_conversion("GBP"), gbp, "GBP")], **common
    )
    await post_transaction(
        db_session,
        [debit(escrow, ngn, "NGN", rate), credit(accounts.fx_conversion("NGN"), ngn, "NGN", rate)],
        **common,
    )

    assert await balance(db_session, funding) == 0
    assert await balance(db_session, escrow) == ngn
    page = await list_entries(db_session, ref_id=event_id)
    assert len(page.items) == 6
    assert [e.fx_rate for e in page.items if e.currency == "NGN"] == [rate, rate]


async def test_balance_of_unknown_account_is_zero(db_session: AsyncSession) -> None:
    assert await balance(db_session, accounts.escrow(uuid.uuid4(), "NGN")) == 0


async def test_balance_refuses_account_holding_two_currencies(db_session: AsyncSession) -> None:
    account = f"test_mixed:{uuid.uuid4()}"
    for cur in ("GBP", "NGN"):
        await post_transaction(
            db_session,
            [debit(account, 10, cur), credit(f"other:{cur}", 10, cur)],
            ref_type="t",
            ref_id=uuid.uuid4(),
        )
    with pytest.raises(AppError) as err:
        await balance(db_session, account)
    assert err.value.code == "ledger_mixed_currency"


A, B = "test:a:GBP", "test:b:GBP"


@pytest.mark.parametrize(
    ("entries", "code"),
    [
        ([], "ledger_unbalanced"),
        ([debit(A, 100, "GBP")], "ledger_unbalanced"),
        ([debit(A, 100, "GBP"), credit(B, 99, "GBP")], "ledger_unbalanced"),
        ([debit(A, 100, "GBP"), debit(B, 100, "GBP")], "ledger_unbalanced"),
        ([debit(A, 100, "GBP"), credit(B, 100, "NGN")], "ledger_mixed_currency"),
        ([debit(A, 0, "GBP"), credit(B, 0, "GBP")], "ledger_invalid_amount"),
        ([debit(A, -100, "GBP"), credit(B, -100, "GBP")], "ledger_invalid_amount"),
        ([debit(A, 100.0, "GBP"), credit(B, 100.0, "GBP")], "ledger_invalid_amount"),  # type: ignore[arg-type]
        ([debit(A, Decimal(100), "GBP"), credit(B, 100, "GBP")], "ledger_invalid_amount"),  # type: ignore[arg-type]
        ([debit(A, True, "GBP"), credit(B, 1, "GBP")], "ledger_invalid_amount"),
        ([debit(A, 100, "gbp"), credit(B, 100, "gbp")], "ledger_invalid_entry"),
        ([Entry(A, "refund", 100, "GBP"), credit(B, 100, "GBP")], "ledger_invalid_entry"),  # type: ignore[arg-type]
        ([debit(A, 100, "GBP", 1.5), credit(B, 100, "GBP")], "ledger_invalid_entry"),  # type: ignore[arg-type]
        ([debit("", 100, "GBP"), credit(B, 100, "GBP")], "ledger_invalid_entry"),
    ],
    ids=[
        "empty",
        "single-entry",
        "debits-ne-credits",
        "no-credit-side",
        "mixed-currency",
        "zero",
        "negative",
        "float-amount",
        "decimal-amount",
        "bool-amount",
        "lowercase-currency",
        "bad-direction",
        "float-fx-rate",
        "empty-account",
    ],
)
async def test_service_refuses_invalid_transactions(
    db_session: AsyncSession, entries: list[Entry], code: str
) -> None:
    ref_id = uuid.uuid4()
    with pytest.raises(AppError) as err:
        await post_transaction(db_session, entries, ref_type="test", ref_id=ref_id)
    assert err.value.code == code
    assert err.value.status_code == 422
    assert (await list_entries(db_session, ref_id=ref_id)).items == []


async def test_post_transaction_does_not_commit(session_factory: async_sessionmaker[AsyncSession]) -> None:
    ref_id = uuid.uuid4()
    async with session_factory() as session:
        await post_transaction(
            session, [debit(A, 5, "GBP"), credit(B, 5, "GBP")], ref_type="test", ref_id=ref_id
        )
        await session.rollback()  # the caller decides; nothing was committed behind its back
    async with session_factory() as session:
        assert (await list_entries(session, ref_id=ref_id)).items == []


async def test_list_entries_paginates_with_cursor(db_session: AsyncSession) -> None:
    project_id = uuid.uuid4()
    account = accounts.escrow(project_id, "NGN")
    for amount in (1, 2, 3):
        await post_transaction(
            db_session,
            [debit(account, amount, "NGN"), credit(accounts.fx_conversion("NGN"), amount, "NGN")],
            ref_type="test",
            ref_id=uuid.uuid4(),
        )

    seen: list[uuid.UUID] = []
    cursor: str | None = None
    pages = 0
    while True:
        page = await list_entries(db_session, account=account, cursor=cursor, limit=2)
        seen.extend(e.id for e in page.items)
        pages += 1
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    assert pages == 2
    assert len(seen) == len(set(seen)) == 3
    assert await balance(db_session, account) == 6


async def test_list_entries_filters_by_time(db_session: AsyncSession) -> None:
    ref_id = uuid.uuid4()
    await post_transaction(
        db_session, [debit(A, 7, "GBP"), credit(B, 7, "GBP")], ref_type="test", ref_id=ref_id
    )
    created = (await list_entries(db_session, ref_id=ref_id)).items[0].created_at

    assert len((await list_entries(db_session, ref_id=ref_id, since=created)).items) == 2
    assert (await list_entries(db_session, ref_id=ref_id, until=created)).items == []


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"cursor": "not-a-cursor"}, "invalid_cursor"),
        ({"limit": 0}, "invalid_limit"),
        ({"limit": 201}, "invalid_limit"),
    ],
)
async def test_list_entries_refuses_bad_paging(
    db_session: AsyncSession, kwargs: dict[str, Any], code: str
) -> None:
    with pytest.raises(AppError) as err:
        await list_entries(db_session, **kwargs)
    assert err.value.code == code
