"""escrow.partner_balances(): what the partner holds per project, for James's reconciliation."""

import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.escrow import service as escrow
from app.features.escrow.models import EscrowRelease
from app.features.escrow.providers import Balance
from app.features.escrow.tests.factories import FOUNDATION_NGN, make_active_project, simulated_escrow
from app.features.escrow.tests.release_helpers import hold_milestone


@pytest.fixture(autouse=True)
def _fresh_escrow() -> Iterator[None]:
    simulated_escrow().reset()
    yield
    simulated_escrow().reset()


def mine(balances: list[escrow.PartnerBalance], project_id: uuid.UUID) -> list[escrow.PartnerBalance]:
    return [b for b in balances if b.project_id == project_id]


async def test_simulated_partner_reads_escrow_records(db_session: AsyncSession) -> None:
    funded = await make_active_project(db_session)
    hold = await hold_milestone(db_session, funded.project.id, funded.foundation)

    assert mine(await escrow.partner_balances(db_session), funded.project.id) == [
        escrow.PartnerBalance(funded.project.id, "NGN", FOUNDATION_NGN, "records")
    ]

    # Only releases the partner confirmed count; requested or failed ones don't.
    for milestone, status, amount in (
        (funded.blockwork, "released", 1_000_000),
        (funded.foundation, "requested", 2_000),
        (funded.foundation, "failed", 3_000),
    ):
        db_session.add(
            EscrowRelease(
                project_id=funded.project.id,
                milestone_id=milestone.id,
                hold_id=hold.id,
                payee=f"contractor:{funded.contractor.id}",
                amount_minor=amount,
                currency="NGN",
                status=status,
                requested_at=hold.created_at,
            )
        )
    await db_session.flush()

    [balance] = mine(await escrow.partner_balances(db_session), funded.project.id)
    assert balance.available_minor == FOUNDATION_NGN - 1_000_000


async def test_project_without_holds_is_not_listed(db_session: AsyncSession) -> None:
    funded = await make_active_project(db_session)
    assert mine(await escrow.partner_balances(db_session), funded.project.id) == []


async def test_a_real_partner_is_asked(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)
    asked: list[uuid.UUID] = []

    class Partner:
        async def balance(self, project_id: uuid.UUID) -> Balance:
            asked.append(project_id)
            return Balance(project_id, "NGN", held_minor=500, released_minor=200, available_minor=300)

    monkeypatch.setattr(escrow, "get_escrow_settings", lambda: SimpleNamespace(escrow_provider="partner"))
    monkeypatch.setattr(escrow, "get_escrow_provider", lambda: Partner())

    assert mine(await escrow.partner_balances(db_session), funded.project.id) == [
        escrow.PartnerBalance(funded.project.id, "NGN", 300, "partner")
    ]
    assert funded.project.id in asked
