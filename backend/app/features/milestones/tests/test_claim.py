"""POST /milestones/{id}/claim, and the audit entry every transition writes."""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.actor import Actor, current_actor
from app.base.audit.models import AuditEntry
from app.core.db import get_session
from app.core.errors import AppError
from app.features.milestones import project_check, service
from app.features.milestones.models import Milestone
from app.features.milestones.models import MilestoneStatus as S
from app.features.milestones.project_check import ProjectInfo
from app.features.milestones.transitions import ActorRole
from app.main import app

CONTRACTOR = Actor(id=uuid.uuid4(), role="contractor")


async def make_milestone(session: AsyncSession, status: S = S.FUNDED) -> Milestone:
    milestone = Milestone(
        project_id=uuid.uuid4(), sequence=1, name="Foundation", amount_minor=150_000_000, currency="NGN"
    )
    milestone.status = status
    session.add(milestone)
    await session.flush()
    return milestone


def project_is(
    monkeypatch: pytest.MonkeyPatch, status: str = "active", contractor_id: uuid.UUID = CONTRACTOR.id
) -> None:
    async def fake(_: AsyncSession, project_id: uuid.UUID) -> ProjectInfo:
        return ProjectInfo(id=project_id, status=status, contractor_id=contractor_id)

    monkeypatch.setattr(project_check, "get_project_info", fake)


async def audit_entries(session: AsyncSession, milestone_id: uuid.UUID) -> list[AuditEntry]:
    result = await session.scalars(
        select(AuditEntry).where(AuditEntry.object_id == milestone_id).order_by(AuditEntry.at)
    )
    return list(result)


# --- every transition is audited ---------------------------------------------------------------


async def test_transition_writes_an_audit_entry(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.FUNDED)
    supervisor_id = uuid.uuid4()
    await service.transition(db_session, milestone.id, S.CLAIMED, ActorRole.CONTRACTOR, CONTRACTOR.id)
    await service.transition(db_session, milestone.id, S.VERIFIED, ActorRole.SUPERVISOR, supervisor_id)

    entries = await audit_entries(db_session, milestone.id)
    assert [e.action for e in entries] == ["milestone.claimed", "milestone.verified"]
    assert [e.actor_id for e in entries] == [CONTRACTOR.id, supervisor_id]
    assert entries[0].object_type == "milestone"
    assert entries[0].before is not None and entries[0].before["status"] == "funded"
    assert entries[0].after is not None and entries[0].after["status"] == "claimed"
    assert entries[0].after["actor_role"] == "contractor"


async def test_system_transition_has_no_actor(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.PENDING)
    await service.mark_funded(db_session, milestone.id)
    [entry] = await audit_entries(db_session, milestone.id)
    assert (entry.action, entry.actor_id) == ("milestone.funded", None)


async def test_refused_transition_writes_nothing(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.PENDING)
    with pytest.raises(Exception, match="cannot move"):
        await service.transition(db_session, milestone.id, S.RELEASED, ActorRole.SYSTEM)
    assert await audit_entries(db_session, milestone.id) == []


# --- service.claim() ---------------------------------------------------------------------------


async def test_contractor_claims_a_funded_milestone(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_is(monkeypatch)
    milestone = await make_milestone(db_session)
    result = await service.claim(db_session, milestone.id, CONTRACTOR)
    assert result.status == S.CLAIMED
    assert result.claimed_at is not None


@pytest.mark.parametrize(
    ("actor", "project_status", "milestone_status", "status_code", "code"),
    [
        (Actor(uuid.uuid4(), "supervisor"), "active", S.FUNDED, 403, "transition_not_allowed"),
        (Actor(uuid.uuid4(), "client"), "active", S.FUNDED, 403, "transition_not_allowed"),
        (Actor(uuid.uuid4(), "contractor"), "active", S.FUNDED, 403, "not_project_contractor"),
        (CONTRACTOR, "paused", S.FUNDED, 409, "project_not_active"),
        (CONTRACTOR, "boq_review", S.FUNDED, 409, "project_not_active"),
        (CONTRACTOR, "active", S.PENDING, 409, "invalid_transition"),
        (CONTRACTOR, "active", S.CLAIMED, 409, "invalid_transition"),
        (CONTRACTOR, "active", S.RELEASED, 409, "invalid_transition"),
    ],
)
async def test_claim_is_refused(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    actor: Actor,
    project_status: str,
    milestone_status: S,
    status_code: int,
    code: str,
) -> None:
    project_is(monkeypatch, status=project_status)
    milestone = await make_milestone(db_session, milestone_status)
    with pytest.raises(AppError) as error:
        await service.claim(db_session, milestone.id, actor)
    assert (error.value.status_code, error.value.code) == (status_code, code)
    assert (await service.get_milestone(db_session, milestone.id)).status == milestone_status


async def test_claim_waits_for_projects_to_be_connected(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session)
    with pytest.raises(AppError) as error:
        await service.claim(db_session, milestone.id, CONTRACTOR)
    assert error.value.code == "projects_not_ready"


# --- POST /milestones/{id}/claim ---------------------------------------------------------------


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def override_actor() -> Actor:
        return CONTRACTOR

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[current_actor] = override_actor
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()


async def test_claim_endpoint(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_is(monkeypatch)
    milestone = await make_milestone(db_session)
    response = await client.post(
        f"/api/v1/milestones/{milestone.id}/claim", headers={"X-Device-Id": "tecno-spark-20"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "claimed"

    [entry] = await audit_entries(db_session, milestone.id)
    assert (entry.action, entry.actor_id, entry.device_id) == (
        "milestone.claimed",
        CONTRACTOR.id,
        "tecno-spark-20",
    )


async def test_claim_retry_with_same_key_returns_first_answer(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_is(monkeypatch)
    milestone = await make_milestone(db_session)
    url = f"/api/v1/milestones/{milestone.id}/claim"
    headers = {"Idempotency-Key": str(uuid.uuid4())}

    first = await client.post(url, headers=headers)
    retry = await client.post(url, headers=headers)
    without_key = await client.post(url)

    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    assert len(await audit_entries(db_session, milestone.id)) == 1  # the claim happened once
    assert without_key.status_code == 409  # a new claim on a claimed milestone is still refused


async def test_claim_endpoint_unknown_milestone(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    project_is(monkeypatch)
    response = await client.post(f"/api/v1/milestones/{uuid.uuid4()}/claim")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "milestone_not_found"


async def test_claim_endpoint_is_closed_until_sign_in_is_connected(db_session: AsyncSession) -> None:
    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.post(f"/api/v1/milestones/{uuid.uuid4()}/claim")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "auth_not_ready"
