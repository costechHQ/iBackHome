"""POST /milestones/{id}/claim, and the audit entry every transition writes.

Every milestone here belongs to a real project (milestones.project_id is a foreign key).
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.actor import Actor
from app.base.audit.models import AuditEntry
from app.base.users.models import User
from app.core.errors import AppError
from app.features.milestones import service
from app.features.milestones.models import Milestone
from app.features.milestones.models import MilestoneStatus as S
from app.features.milestones.tests.factories import bearer, make_project, make_user
from app.features.milestones.transitions import ActorRole


def actor(user: User) -> Actor:
    return Actor(id=user.id, role=user.role)


async def make_milestone(
    session: AsyncSession,
    status: S = S.FUNDED,
    *,
    contractor: User | None = None,
    project_status: str = "active",
) -> Milestone:
    """A milestone on a real project whose contractor is `contractor` (a new one if None)."""
    contractor = contractor or await make_user(session, "contractor")
    project = await make_project(session, contractor=contractor, status=project_status)
    milestone = Milestone(
        project_id=project.id, sequence=1, name="Foundation", amount_minor=150_000_000, currency="NGN"
    )
    milestone.status = status
    session.add(milestone)
    await session.flush()
    return milestone


async def audit_entries(session: AsyncSession, milestone_id: uuid.UUID) -> list[AuditEntry]:
    result = await session.scalars(
        select(AuditEntry).where(AuditEntry.object_id == milestone_id).order_by(AuditEntry.at)
    )
    return list(result)


# --- every transition is audited ---------------------------------------------------------------


async def test_transition_writes_an_audit_entry(db_session: AsyncSession) -> None:
    milestone = await make_milestone(db_session, S.FUNDED)
    contractor_id, supervisor_id = uuid.uuid4(), uuid.uuid4()
    await service.transition(db_session, milestone.id, S.CLAIMED, ActorRole.CONTRACTOR, contractor_id)
    await service.transition(db_session, milestone.id, S.VERIFIED, ActorRole.SUPERVISOR, supervisor_id)

    entries = await audit_entries(db_session, milestone.id)
    assert [e.action for e in entries] == ["milestone.claimed", "milestone.verified"]
    assert [e.actor_id for e in entries] == [contractor_id, supervisor_id]
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


async def test_a_milestone_needs_a_real_project(db_session: AsyncSession) -> None:
    """The foreign key milestones.project_id -> projects.id."""
    orphan = Milestone(project_id=uuid.uuid4(), sequence=1, name="Foundation", amount_minor=1, currency="NGN")
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(orphan)
            await db_session.flush()


# --- service.claim() ---------------------------------------------------------------------------


async def test_contractor_claims_a_funded_milestone(db_session: AsyncSession) -> None:
    contractor = await make_user(db_session, "contractor")
    milestone = await make_milestone(db_session, contractor=contractor)
    result = await service.claim(db_session, milestone.id, actor(contractor))
    assert result.status == S.CLAIMED
    assert result.claimed_at is not None


@pytest.mark.parametrize(
    ("who", "project_status", "milestone_status", "status_code", "code"),
    [
        ("supervisor", "active", S.FUNDED, 403, "transition_not_allowed"),
        ("client", "active", S.FUNDED, 403, "transition_not_allowed"),
        ("other_contractor", "active", S.FUNDED, 403, "not_project_contractor"),
        ("contractor", "paused", S.FUNDED, 409, "project_not_active"),
        ("contractor", "boq_review", S.FUNDED, 409, "project_not_active"),
        ("contractor", "active", S.PENDING, 409, "invalid_transition"),
        ("contractor", "active", S.CLAIMED, 409, "invalid_transition"),
        ("contractor", "active", S.RELEASED, 409, "invalid_transition"),
    ],
)
async def test_claim_is_refused(
    db_session: AsyncSession,
    who: str,
    project_status: str,
    milestone_status: S,
    status_code: int,
    code: str,
) -> None:
    contractor = await make_user(db_session, "contractor")
    milestone = await make_milestone(
        db_session, milestone_status, contractor=contractor, project_status=project_status
    )
    user = contractor if who == "contractor" else await make_user(db_session, who.replace("other_", ""))
    with pytest.raises(AppError) as error:
        await service.claim(db_session, milestone.id, actor(user))
    assert (error.value.status_code, error.value.code) == (status_code, code)
    assert (await service.get_milestone(db_session, milestone.id)).status == milestone_status


# --- POST /milestones/{id}/claim ---------------------------------------------------------------


async def test_claim_endpoint(client: AsyncClient, db_session: AsyncSession) -> None:
    contractor = await make_user(db_session, "contractor")
    milestone = await make_milestone(db_session, contractor=contractor)
    response = await client.post(
        f"/api/v1/milestones/{milestone.id}/claim",
        headers={**bearer(contractor), "X-Device-Id": "tecno-spark-20"},
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
    client: AsyncClient, db_session: AsyncSession
) -> None:
    contractor = await make_user(db_session, "contractor")
    milestone = await make_milestone(db_session, contractor=contractor)
    url = f"/api/v1/milestones/{milestone.id}/claim"
    auth = bearer(contractor)
    headers = {**auth, "Idempotency-Key": str(uuid.uuid4())}

    first = await client.post(url, headers=headers)
    retry = await client.post(url, headers=headers)
    without_key = await client.post(url, headers=auth)

    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    assert len(await audit_entries(db_session, milestone.id)) == 1  # the claim happened once
    assert without_key.status_code == 409  # a new claim on a claimed milestone is still refused


async def test_claim_endpoint_unknown_milestone(client: AsyncClient, db_session: AsyncSession) -> None:
    contractor = await make_user(db_session, "contractor")
    response = await client.post(f"/api/v1/milestones/{uuid.uuid4()}/claim", headers=bearer(contractor))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "milestone_not_found"


async def test_claim_endpoint_needs_sign_in(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/milestones/{uuid.uuid4()}/claim")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["client", "supervisor", "supplier", "ops"])
async def test_claim_endpoint_is_for_contractors_only(
    client: AsyncClient, db_session: AsyncSession, role: str
) -> None:
    user = await make_user(db_session, role)
    milestone = await make_milestone(db_session)
    response = await client.post(f"/api/v1/milestones/{milestone.id}/claim", headers=bearer(user))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"
    assert await audit_entries(db_session, milestone.id) == []
