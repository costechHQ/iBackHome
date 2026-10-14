import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.features.evidence import service
from app.features.evidence.tests.conftest import World, add_evidence, bearer, make_world


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    return await make_world(db_session)


def url(evidence_id: uuid.UUID) -> str:
    return f"/api/v1/evidence/{evidence_id}/decision"


async def test_ops_accepts_flagged_evidence(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    row = await add_evidence(db_session, world, status="flagged", reason="Looks like evidence X")
    response = await client.post(
        url(row.id), json={"decision": "accepted", "notes": "Different building"}, headers=bearer(world.ops)
    )
    assert response.status_code == 200
    out = response.json()
    assert out["status"] == "accepted"
    assert out["reject_reason"] is None
    entry = await db_session.scalar(
        select(AuditEntry).where(AuditEntry.object_id == row.id, AuditEntry.action == "evidence.ops_accepted")
    )
    assert entry is not None
    assert entry.actor_id == world.ops.id
    assert entry.before is not None and entry.before["status"] == "flagged"
    assert entry.after is not None and entry.after["ops_notes"] == "Different building"


async def test_an_ops_accepted_photo_counts_toward_verification(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    row = await add_evidence(db_session, world, status="flagged")
    assert await service.accepted_for_milestone(db_session, world.milestone.id) == []
    await client.post(url(row.id), json={"decision": "accepted"}, headers=bearer(world.ops))
    assert [e.id for e in await service.accepted_for_milestone(db_session, world.milestone.id)] == [row.id]


async def test_ops_rejects_flagged_evidence_with_notes(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    row = await add_evidence(db_session, world, status="flagged")
    response = await client.post(
        url(row.id),
        json={"decision": "rejected", "notes": "Same photo as project 12"},
        headers=bearer(world.ops),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["reject_reason"] == "Ops: Same photo as project 12"
    assert await service.accepted_for_milestone(db_session, world.milestone.id) == []


async def test_rejecting_needs_notes(client: AsyncClient, db_session: AsyncSession, world: World) -> None:
    row = await add_evidence(db_session, world, status="flagged")
    for body in ({"decision": "rejected"}, {"decision": "rejected", "notes": "   "}):
        response = await client.post(url(row.id), json=body, headers=bearer(world.ops))
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "notes_required"


async def test_only_flagged_evidence_can_be_decided(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    for status in ("pending_checks", "accepted", "rejected"):
        row = await add_evidence(db_session, world, status=status)
        response = await client.post(
            url(row.id), json={"decision": "accepted", "notes": "x"}, headers=bearer(world.ops)
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "invalid_evidence_transition"


async def test_a_decision_cannot_be_made_twice(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    row = await add_evidence(db_session, world, status="flagged")
    first = await client.post(url(row.id), json={"decision": "accepted"}, headers=bearer(world.ops))
    second = await client.post(
        url(row.id), json={"decision": "rejected", "notes": "changed my mind"}, headers=bearer(world.ops)
    )
    assert first.status_code == 200
    assert second.status_code == 409


async def test_the_same_idempotency_key_replays_the_answer(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    row = await add_evidence(db_session, world, status="flagged")
    headers = bearer(world.ops) | {"Idempotency-Key": "decide-1"}
    first = await client.post(url(row.id), json={"decision": "accepted"}, headers=headers)
    second = await client.post(url(row.id), json={"decision": "accepted"}, headers=headers)
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    entries = list(
        await db_session.scalars(
            select(AuditEntry).where(
                AuditEntry.object_id == row.id, AuditEntry.action == "evidence.ops_accepted"
            )
        )
    )
    assert len(entries) == 1


async def test_only_ops_can_decide(client: AsyncClient, db_session: AsyncSession, world: World) -> None:
    row = await add_evidence(db_session, world, status="flagged")
    for who in (world.supervisor, world.contractor, world.client):
        response = await client.post(url(row.id), json={"decision": "accepted"}, headers=bearer(who))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden_role"
    assert (await client.post(url(row.id), json={"decision": "accepted"})).status_code == 401
    await db_session.refresh(row)
    assert row.status == "flagged"


async def test_unknown_evidence_is_404_and_bad_decisions_are_422(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    missing = await client.post(url(uuid.uuid4()), json={"decision": "accepted"}, headers=bearer(world.ops))
    assert missing.status_code == 404
    row = await add_evidence(db_session, world, status="flagged")
    for body in ({"decision": "flagged"}, {"decision": "maybe"}, {}):
        assert (await client.post(url(row.id), json=body, headers=bearer(world.ops))).status_code == 422
