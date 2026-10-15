import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.core.errors import AppError
from app.features.evidence import checks, tasks
from app.features.evidence.tests.conftest import World, add_evidence, make_world


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    return await make_world(db_session)


# The task itself (no database: the work it calls is replaced)


def test_a_brief_outage_is_retried_until_the_checks_run(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    async def flaky(evidence_id: uuid.UUID) -> str:
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("storage is down")
        return "accepted"

    monkeypatch.setattr(tasks, "_run", flaky)
    result = tasks.run_checks.apply(args=[str(uuid.uuid4())])
    assert result.get() == "accepted"
    assert len(calls) == 3


def test_checks_that_never_run_are_flagged_for_ops_not_left_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[int] = []
    flagged: list[tuple[uuid.UUID, str]] = []

    async def down(evidence_id: uuid.UUID) -> str:
        attempts.append(1)
        raise ConnectionError("database is down")

    async def flag(evidence_id: uuid.UUID, reason: str) -> str:
        flagged.append((evidence_id, reason))
        return "flagged"

    monkeypatch.setattr(tasks, "_run", down)
    monkeypatch.setattr(tasks, "_flag_unchecked", flag)
    target = uuid.uuid4()
    result = tasks.run_checks.apply(args=[str(target)])
    assert result.get() == "flagged"
    assert len(attempts) == tasks.MAX_RETRIES + 1
    assert [f[0] for f in flagged] == [target]
    assert "ops must review" in flagged[0][1]


def test_a_real_answer_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    async def missing(evidence_id: uuid.UUID) -> str:
        calls.append(1)
        raise AppError("evidence_not_found", "Evidence not found.", 404)

    monkeypatch.setattr(tasks, "_run", missing)
    result = tasks.run_checks.apply(args=[str(uuid.uuid4())])
    assert result.failed()
    assert len(calls) == 1


def test_waits_grow_and_are_capped() -> None:
    waits = [tasks.retry_delay(n) for n in range(tasks.MAX_RETRIES + 1)]
    assert all(0 < w <= tasks.RETRY_MAX_S for w in waits)
    assert tasks.retry_delay(0) <= tasks.RETRY_BASE_S
    assert tasks.retry_delay(20) >= tasks.RETRY_MAX_S * 0.75


# The fallback (database)


async def test_flag_unchecked_sends_a_pending_capture_to_ops(db_session: AsyncSession, world: World) -> None:
    row = await add_evidence(db_session, world, status="pending_checks")
    out = await checks.flag_unchecked(db_session, row.id, "Checks could not run.")
    assert out.status == "flagged"
    assert out.reject_reason == "Checks could not run."
    entry = await db_session.scalar(
        select(AuditEntry).where(AuditEntry.object_id == row.id, AuditEntry.action == "evidence.flagged")
    )
    assert entry is not None and entry.actor_id is None


@pytest.mark.parametrize("status", ["accepted", "rejected", "flagged"])
async def test_flag_unchecked_never_overwrites_a_decision(
    db_session: AsyncSession, world: World, status: str
) -> None:
    row = await add_evidence(db_session, world, status=status)
    out: Any = await checks.flag_unchecked(db_session, row.id, "Checks could not run.")
    assert out.status == status
    assert out.reject_reason != "Checks could not run."


async def test_flag_unchecked_unknown_evidence_is_404(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as err:
        await checks.flag_unchecked(db_session, uuid.uuid4(), "x")
    assert err.value.status_code == 404
