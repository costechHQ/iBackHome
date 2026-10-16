import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.escrow.models import Dispute
from app.features.evidence.tests.conftest import World, add_evidence, bearer, make_user, make_world
from app.features.ops import disputes_bridge
from app.features.supervision import service as supervision
from app.features.supervision.schemas import SupervisorApplication, VettingDecision

URL = "/api/v1/ops/queue"


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    return await make_world(db_session)


async def apply(db_session: AsyncSession, number: str = "R1") -> User:
    supervisor = await make_user(db_session, "supervisor")
    await supervision.submit_application(
        db_session,
        supervisor.id,
        SupervisorApplication(
            registration_body="COREN",
            registration_no=number,
            guarantor_1="Ngozi Eze, +2348031234567",
            guarantor_2="Emeka Obi, +2348037654321",
            related_contractors=[],
        ),
    )
    return supervisor


async def test_ops_sees_one_queue_with_everything_waiting(
    client: AsyncClient, db_session: AsyncSession, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    applicant = await apply(db_session)
    flagged = await add_evidence(db_session, world, status="flagged", reason="Looks like evidence X")
    await add_evidence(db_session, world, status="accepted")  # not waiting for anyone
    dispute = disputes_bridge.OpenDispute(
        id=uuid.uuid4(),
        project_id=world.project.id,
        milestone_id=world.milestone.id,
        reason="Foundation is cracked",
        created_at=datetime(2026, 10, 15, 8, 0, tzinfo=UTC),
    )

    async def open_disputes(session: AsyncSession, limit: int) -> list[disputes_bridge.OpenDispute]:
        return [dispute]

    monkeypatch.setattr(disputes_bridge, "list_open", open_disputes)

    response = await client.get(URL, headers=bearer(world.ops))
    assert response.status_code == 200
    body = response.json()
    assert [v["user_id"] for v in body["vetting"]] == [str(applicant.id)]
    assert body["vetting"][0]["registration_body"] == "COREN"
    assert [f["evidence_id"] for f in body["flagged_evidence"]] == [str(flagged.id)]
    assert body["flagged_evidence"][0]["reason"] == "Looks like evidence X"
    assert body["flagged_evidence"][0]["project_id"] == str(world.project.id)
    assert [d["dispute_id"] for d in body["disputes"]] == [str(dispute.id)]
    assert body["disputes"][0]["reason"] == "Foundation is cracked"


async def test_an_empty_queue_is_three_empty_lists(client: AsyncClient, world: World) -> None:
    response = await client.get(URL, headers=bearer(world.ops))
    assert response.status_code == 200
    body = response.json()
    assert {k: len(v) for k, v in body.items()} == {"vetting": 0, "flagged_evidence": 0, "disputes": 0}


async def test_items_leave_the_queue_once_decided(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    applicant = await apply(db_session)
    flagged = await add_evidence(db_session, world, status="flagged")
    await client.post(
        f"/api/v1/evidence/{flagged.id}/decision", json={"decision": "accepted"}, headers=bearer(world.ops)
    )
    ops = world.ops
    await supervision.vet(
        db_session,
        applicant.id,
        VettingDecision(
            decision="approved",
            registration_verified=True,
            nin_verified=True,
            guarantor_1_verified=True,
            guarantor_2_verified=True,
        ),
        ops.id,
    )
    body = (await client.get(URL, headers=bearer(world.ops))).json()
    assert body["vetting"] == [] and body["flagged_evidence"] == []


async def test_lists_are_oldest_first_and_can_be_capped(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    start = datetime(2026, 10, 15, 8, 0, tzinfo=UTC)
    first = await add_evidence(db_session, world, status="flagged", created_at=start)
    second = await add_evidence(db_session, world, status="flagged", created_at=start + timedelta(minutes=1))
    third = await add_evidence(db_session, world, status="flagged", created_at=start + timedelta(minutes=2))
    ids = [str(e.id) for e in (first, second, third)]
    body = (await client.get(URL, headers=bearer(world.ops))).json()
    assert [f["evidence_id"] for f in body["flagged_evidence"]] == ids
    capped = (await client.get(URL, params={"limit": 2}, headers=bearer(world.ops))).json()
    assert [f["evidence_id"] for f in capped["flagged_evidence"]] == ids[:2]
    assert (await client.get(URL, params={"limit": 0}, headers=bearer(world.ops))).status_code == 422


async def test_only_ops_can_see_the_queue(client: AsyncClient, world: World) -> None:
    for who in (world.client, world.contractor, world.supervisor):
        response = await client.get(URL, headers=bearer(who))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden_role"
    assert (await client.get(URL)).status_code == 401


async def test_without_gabriels_disputes_there_are_simply_none(client: AsyncClient, world: World) -> None:
    # The bridge returns an empty list until his disputes exist, because none can be open yet.
    assert (await client.get(URL, headers=bearer(world.ops))).json()["disputes"] == []


async def test_a_real_open_dispute_shows_in_the_queue(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    """The bridge reads Gabriel's escrow.list_open_disputes(); resolved disputes don't show."""
    open_one = Dispute(
        project_id=world.project.id,
        milestone_id=world.milestone.id,
        raised_by=world.client.id,
        reason="Foundation is cracked",
        status="open",
    )
    closed = Dispute(
        project_id=world.project.id,
        milestone_id=world.other_milestone.id,
        raised_by=world.client.id,
        reason="Settled",
        status="resolved_reject",
    )
    db_session.add_all([open_one, closed])
    await db_session.flush()

    response = await client.get(URL, headers=bearer(world.ops))
    assert response.status_code == 200
    disputes = response.json()["disputes"]
    assert [d["dispute_id"] for d in disputes] == [str(open_one.id)]
    assert disputes[0]["reason"] == "Foundation is cracked"
    assert disputes[0]["milestone_id"] == str(world.milestone.id)
