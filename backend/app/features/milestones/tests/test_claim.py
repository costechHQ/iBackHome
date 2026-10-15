"""POST /milestones/{id}/claim, and the audit entry every transition writes."""

import secrets
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.actor import Actor
from app.base.audit.models import AuditEntry
from app.base.users import service as users
from app.base.users.models import User
from app.core.errors import AppError
from app.features.milestones import project_check, service
from app.features.milestones.models import Milestone
from app.features.milestones.models import MilestoneStatus as S
from app.features.milestones.project_check import ProjectInfo
from app.features.milestones.transitions import ActorRole

CONTRACTOR = Actor(id=uuid.uuid4(), role="contractor")


async def sign_in_as(session: AsyncSession, role: str) -> tuple[User, dict[str, str]]:
    """A real user with this role, and the Authorization header for their access token."""
    user = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role=role, status="active")
    session.add(user)
    await session.flush()
    return user, {"Authorization": f"Bearer {users.create_access_token(user)}"}


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


async def test_claim_on_a_missing_project_is_404(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session)  # its project_id points at no project
    with pytest.raises(AppError) as error:
        await service.claim(db_session, milestone.id, CONTRACTOR)
    assert (error.value.status_code, error.value.code) == (404, "project_not_found")


# --- POST /milestones/{id}/claim ---------------------------------------------------------------


async def test_claim_endpoint(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    contractor, headers = await sign_in_as(db_session, "contractor")
    project_is(monkeypatch, contractor_id=contractor.id)
    milestone = await make_milestone(db_session)
    response = await client.post(
        f"/api/v1/milestones/{milestone.id}/claim", headers={**headers, "X-Device-Id": "tecno-spark-20"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "claimed"

    [entry] = await audit_entries(db_session, milestone.id)
    assert (entry.action, entry.actor_id, entry.device_id) == (
        "milestone.claimed",
        contractor.id,
        "tecno-spark-20",
    )


async def test_claim_retry_with_same_key_returns_first_answer(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    contractor, auth = await sign_in_as(db_session, "contractor")
    project_is(monkeypatch, contractor_id=contractor.id)
    milestone = await make_milestone(db_session)
    url = f"/api/v1/milestones/{milestone.id}/claim"
    headers = {**auth, "Idempotency-Key": str(uuid.uuid4())}

    first = await client.post(url, headers=headers)
    retry = await client.post(url, headers=headers)
    without_key = await client.post(url, headers=auth)

    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    assert len(await audit_entries(db_session, milestone.id)) == 1  # the claim happened once
    assert without_key.status_code == 409  # a new claim on a claimed milestone is still refused


async def test_claim_endpoint_unknown_milestone(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    contractor, headers = await sign_in_as(db_session, "contractor")
    project_is(monkeypatch, contractor_id=contractor.id)
    response = await client.post(f"/api/v1/milestones/{uuid.uuid4()}/claim", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "milestone_not_found"


async def test_claim_endpoint_needs_sign_in(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/milestones/{uuid.uuid4()}/claim")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["client", "supervisor", "supplier", "ops"])
async def test_claim_endpoint_is_for_contractors_only(
    client: AsyncClient, db_session: AsyncSession, role: str
) -> None:
    _, headers = await sign_in_as(db_session, role)
    milestone = await make_milestone(db_session)
    response = await client.post(f"/api/v1/milestones/{milestone.id}/claim", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"
    assert await audit_entries(db_session, milestone.id) == []


async def test_claim_endpoint_reads_the_real_project(client: AsyncClient, db_session: AsyncSession) -> None:
    _, headers = await sign_in_as(db_session, "contractor")
    milestone = await make_milestone(db_session)  # its project_id points at no project
    response = await client.post(f"/api/v1/milestones/{milestone.id}/claim", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "project_not_found"
