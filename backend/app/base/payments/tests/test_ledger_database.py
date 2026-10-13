"""What the database itself enforces on ledger_entries, with the Python service bypassed.

These tests commit for real, because the balance trigger is deferred to commit time.
"""

import importlib.util
import uuid
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.base.payments import credit, debit, list_entries, post_transaction
from app.base.payments.settings import get_payments_settings

INSERT = text(
    "INSERT INTO ledger_entries "
    "(id, transaction_id, account, direction, amount_minor, currency, ref_type, ref_id) "
    "VALUES (gen_random_uuid(), :txn, :account, :direction, :amount, :currency, 'raw_sql_test', :ref)"
)


def _row(
    txn: uuid.UUID, ref: uuid.UUID, account: str, direction: str, amount: int, currency: str
) -> dict[str, object]:
    return {
        "txn": txn,
        "ref": ref,
        "account": account,
        "direction": direction,
        "amount": amount,
        "currency": currency,
    }


async def _count(engine: AsyncEngine, ref: uuid.UUID) -> int:
    async with engine.connect() as conn:
        return int(
            (
                await conn.execute(text("SELECT count(*) FROM ledger_entries WHERE ref_id = :r"), {"r": ref})
            ).scalar_one()
        )


async def test_database_rejects_unbalanced_write_at_commit(engine: AsyncEngine) -> None:
    """THE KEY TEST: raw SQL skips post_transaction; the deferred trigger still refuses the commit."""
    txn, ref = uuid.uuid4(), uuid.uuid4()
    async with engine.connect() as conn:
        await conn.execute(INSERT, _row(txn, ref, "raw:a:GBP", "debit", 100_000, "GBP"))
        await conn.execute(INSERT, _row(txn, ref, "raw:b:GBP", "credit", 90_000, "GBP"))
        # Each INSERT succeeded: the check is deferred to commit.
        with pytest.raises(IntegrityError, match="unbalanced"):
            await conn.commit()
    assert await _count(engine, ref) == 0


async def test_database_rejects_mixed_currency_at_commit(engine: AsyncEngine) -> None:
    txn, ref = uuid.uuid4(), uuid.uuid4()
    async with engine.connect() as conn:
        await conn.execute(INSERT, _row(txn, ref, "raw:a:GBP", "debit", 500, "GBP"))
        await conn.execute(INSERT, _row(txn, ref, "raw:b:NGN", "credit", 500, "NGN"))
        with pytest.raises(IntegrityError, match="currencies"):
            await conn.commit()
    assert await _count(engine, ref) == 0


async def test_database_rejects_service_transaction_tampered_before_commit(
    session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
) -> None:
    """Even after post_transaction validated, an extra row in the same transaction_id is caught at commit."""
    ref = uuid.uuid4()
    async with session_factory() as session:
        txn = await post_transaction(
            session,
            [debit("raw:a:GBP", 100, "GBP"), credit("raw:b:GBP", 100, "GBP")],
            ref_type="t",
            ref_id=ref,
        )
        await session.execute(INSERT, _row(txn, ref, "raw:c:GBP", "debit", 1, "GBP"))
        with pytest.raises(IntegrityError, match="unbalanced"):
            await session.commit()
    assert await _count(engine, ref) == 0


@pytest.mark.parametrize("amount", [0, -100])
async def test_database_rejects_non_positive_amount(engine: AsyncEngine, amount: int) -> None:
    async with engine.connect() as conn:
        with pytest.raises(IntegrityError, match="ck_ledger_entries_amount_positive"):
            await conn.execute(INSERT, _row(uuid.uuid4(), uuid.uuid4(), "raw:a:GBP", "debit", amount, "GBP"))


async def test_balanced_raw_write_commits(engine: AsyncEngine) -> None:
    txn, ref = uuid.uuid4(), uuid.uuid4()
    async with engine.connect() as conn:
        await conn.execute(INSERT, _row(txn, ref, "raw:a:GBP", "debit", 300, "GBP"))
        await conn.execute(INSERT, _row(txn, ref, "raw:b:GBP", "credit", 200, "GBP"))
        await conn.execute(INSERT, _row(txn, ref, "raw:c:GBP", "credit", 100, "GBP"))
        await conn.commit()
    assert await _count(engine, ref) == 3


async def _committed_entry(session_factory: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    ref = uuid.uuid4()
    async with session_factory() as session:
        await post_transaction(
            session, [debit("raw:a:GBP", 42, "GBP"), credit("raw:b:GBP", 42, "GBP")], ref_type="t", ref_id=ref
        )
        await session.commit()
    return ref


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE ledger_entries SET amount_minor = 1 WHERE ref_id = :r",
        "DELETE FROM ledger_entries WHERE ref_id = :r",
    ],
    ids=["update", "delete"],
)
async def test_update_and_delete_refused_for_every_role(
    session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine, statement: str
) -> None:
    """The append-only trigger stops even the owner / a superuser (what CI and local dev connect as)."""
    ref = await _committed_entry(session_factory)
    async with engine.connect() as conn:
        with pytest.raises(DBAPIError, match="append-only"):
            await conn.execute(text(statement), {"r": ref})
    async with session_factory() as session:
        assert {e.amount_minor for e in (await list_entries(session, ref_id=ref)).items} == {42}


async def test_truncate_refused(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        with pytest.raises(DBAPIError, match="append-only"):
            await conn.execute(text("TRUNCATE ledger_entries"))


async def test_app_role_has_no_update_or_delete_grant(engine: AsyncEngine) -> None:
    role = get_payments_settings().ledger_app_role
    async with engine.connect() as conn:
        exists = (await conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role})).first()
        if exists is None:
            pytest.skip(f"app role {role!r} does not exist in this database")
        privileges = set(
            (
                await conn.execute(
                    text(
                        "SELECT a.privilege_type FROM pg_class c, aclexplode(c.relacl) a "
                        "WHERE c.relname = 'ledger_entries' AND a.grantee IN "
                        "(SELECT oid FROM pg_roles WHERE rolname = :r UNION SELECT 0)"
                    ),
                    {"r": role},
                )
            ).scalars()
        )
    assert privileges.isdisjoint({"UPDATE", "DELETE", "TRUNCATE"}), privileges


def _migration() -> ModuleType:
    path = next((Path(__file__).parents[4] / "alembic" / "versions").glob("*_create_ledger_entries.py"))
    spec = importlib.util.spec_from_file_location("ledger_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_non_superuser_app_role_gets_permission_denied(engine: AsyncEngine) -> None:
    """Production-shaped role: not the owner, not a superuser. Give it everything, then apply the
    migration's REVOKE; Postgres itself must then deny UPDATE and DELETE (before any trigger runs)."""
    role = f"ledger_test_{uuid.uuid4().hex[:12]}"
    async with engine.connect() as conn:
        await conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
        await conn.execute(text(f'GRANT ALL ON ledger_entries TO "{role}"'))
        await conn.execute(text(_migration()._revoke_sql(role)))
        await conn.execute(text(f'SET LOCAL ROLE "{role}"'))
        for statement in ("UPDATE ledger_entries SET amount_minor = 1", "DELETE FROM ledger_entries"):
            await conn.execute(text("SAVEPOINT s"))
            with pytest.raises(DBAPIError, match="permission denied"):
                await conn.execute(text(statement))
            await conn.execute(text("ROLLBACK TO SAVEPOINT s"))
        await conn.rollback()  # CREATE ROLE is transactional: the test role disappears
