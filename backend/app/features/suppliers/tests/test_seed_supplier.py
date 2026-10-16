"""ensure_supplier(), and the seed's supplier and bank accounts (scripts/seed.py v4)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.payments import get_recipient_for
from app.base.payments.paystack import RecipientResult
from app.base.users.models import User
from app.core.errors import AppError
from app.features.suppliers import service
from scripts import seed


async def seed_people(session: AsyncSession) -> dict[str, User]:
    return {s.key: await seed.upsert_user(session, s) for s in seed.USERS}


# --- ensure_supplier ----------------------------------------------------------------------------


async def test_ensure_supplier_creates_once_and_audits(db_session: AsyncSession) -> None:
    people = await seed_people(db_session)
    first = await service.ensure_supplier(
        db_session,
        " Test Blocks Ltd ",
        owner_id=people["supplier"].id,
        verified=True,
        actor_id=people["ops"].id,
    )
    again = await service.ensure_supplier(db_session, "Test Blocks Ltd", owner_id=people["supplier"].id)

    assert again.id == first.id
    assert (first.name, first.verified, first.owner_id) == ("Test Blocks Ltd", True, people["supplier"].id)
    actions = await db_session.scalars(select(AuditEntry.action).where(AuditEntry.object_id == first.id))
    assert list(actions) == ["supplier.created"]


async def test_ensure_supplier_without_owner_matches_on_name(db_session: AsyncSession) -> None:
    first = await service.ensure_supplier(db_session, "Ownerless Sand Co")
    assert (await service.ensure_supplier(db_session, "Ownerless Sand Co")).id == first.id


async def test_supplier_needs_a_name(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as err:
        await service.ensure_supplier(db_session, "   ")
    assert (err.value.code, err.value.status_code) == ("invalid_supplier_name", 422)


# --- seed v4 ------------------------------------------------------------------------------------


async def test_seed_registers_supplier_and_bank_accounts_idempotently(db_session: AsyncSession) -> None:
    people = await seed_people(db_session)
    supplier = await seed.upsert_supplier(db_session, people["supplier"], people["ops"])
    lines = await seed.register_bank_accounts(db_session, people, supplier, seed.StandInPaystack())
    again = await seed.register_bank_accounts(db_session, people, supplier, seed.StandInPaystack())

    assert supplier.verified and supplier.owner_id == people["supplier"].id
    assert lines == again and len(lines) == 2 and all(line.startswith("bank") for line in lines)
    contractor_account = await get_recipient_for(db_session, user_id=people["contractor"].id)
    supplier_account = await get_recipient_for(db_session, supplier_id=supplier.id)
    assert contractor_account is not None and contractor_account.account_number_masked == "******6789"
    assert supplier_account is not None and supplier_account.account_number_masked == "******4321"


async def test_seed_skips_bank_accounts_without_paystack(db_session: AsyncSession) -> None:
    people = await seed_people(db_session)
    supplier = await seed.upsert_supplier(db_session, people["supplier"], people["ops"])
    assert await seed.register_bank_accounts(db_session, people, supplier, None) == [
        "bank accounts skipped: set PAYSTACK_SECRET_KEY (test key) to register them"
    ]


async def test_a_paystack_refusal_is_reported_and_the_rest_continues(db_session: AsyncSession) -> None:
    class Refusing(seed.StandInPaystack):
        async def create_transfer_recipient(
            self, account_name: str, account_number: str, bank_code: str
        ) -> RecipientResult:
            if account_number == "0123456789":
                raise AppError("paystack_refused", "Could not resolve account name.", 422)
            return await super().create_transfer_recipient(account_name, account_number, bank_code)

    people = await seed_people(db_session)
    supplier = await seed.upsert_supplier(db_session, people["supplier"], people["ops"])
    lines = await seed.register_bank_accounts(db_session, people, supplier, Refusing())

    assert lines[0] == (
        "bank account for contractor not registered: paystack_refused (Could not resolve account name.)"
    )
    assert lines[1].startswith("bank        supplier")


def test_stand_in_is_only_used_locally(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(seed, "get_payments_settings", lambda: type("P", (), {"paystack_secret_key": ""})())
    monkeypatch.setattr(seed, "get_settings", lambda: type("S", (), {"environment": "local"})())
    assert isinstance(seed.paystack_for_seed(), seed.StandInPaystack)
    monkeypatch.setattr(seed, "get_settings", lambda: type("S", (), {"environment": "staging"})())
    assert seed.paystack_for_seed() is None
