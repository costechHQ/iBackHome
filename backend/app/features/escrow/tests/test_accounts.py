"""escrow_accounts: one per project, created on first use, balance cached from the ledger."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.escrow import service as escrow
from app.features.escrow.models import EscrowAccount
from app.features.projects.tests.factories import make_project


async def test_get_or_create_account_is_idempotent(db_session: AsyncSession) -> None:
    project = await make_project(db_session)

    first = await escrow.get_or_create_account(db_session, project.id)
    second = await escrow.get_or_create_account(db_session, project.id, lock=True)

    assert first.id == second.id
    assert (first.provider, first.currency, first.balance_minor) == ("simulated", "NGN", 0)
    count = await db_session.scalar(
        select(func.count()).select_from(EscrowAccount).where(EscrowAccount.project_id == project.id)
    )
    assert count == 1


async def test_account_in_another_currency_is_refused(db_session: AsyncSession) -> None:
    project = await make_project(db_session)
    await escrow.get_or_create_account(db_session, project.id, "NGN")

    with pytest.raises(AppError) as error:
        await escrow.get_or_create_account(db_session, project.id, "GBP")

    assert (error.value.status_code, error.value.code) == (409, "escrow_currency_mismatch")
