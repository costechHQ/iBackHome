"""Disputes: POST /milestones/{id}/disputes (client) and POST /disputes/{id}/resolve (two different
ops users). While a dispute is open nothing can be released."""

import uuid
from collections.abc import Iterator

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import accounts, balance
from app.base.payments import service as payments_service
from app.base.users.models import User
from app.core.errors import AppError
from app.features.escrow import service as escrow
from app.features.escrow import tasks as escrow_tasks
from app.features.escrow.tests.factories import FOUNDATION_NGN, Funded, make_active_project, simulated_escrow
from app.features.escrow.tests.release_helpers import (
    Queued,
    add_recipient,
    hold_milestone,
    session_factory,
)
from app.features.milestones import service as milestones
from app.features.milestones.models import Milestone, MilestoneStatus
from app.features.milestones.transitions import ActorRole
from app.features.projects.tests.factories import audit_entries, bearer, make_user


@pytest.fixture(autouse=True)
def _fresh_escrow() -> Iterator[None]:
    simulated_escrow().reset()
    yield
    simulated_escrow().reset()


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> Queued:
    spy = Queued()
    monkeypatch.setattr(escrow, "enqueue_submit_release", spy.releases.append)
    monkeypatch.setattr(payments_service, "enqueue_send_transfer", spy.payouts.append)
    return spy


async def verified(db_session: AsyncSession) -> Funded:
    """Foundation held in escrow, claimed by the contractor and verified by the supervisor."""
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)
    await milestones.transition(
        db_session, funded.foundation.id, MilestoneStatus.CLAIMED, ActorRole.CONTRACTOR, funded.contractor.id
    )
    await milestones.transition(
        db_session, funded.foundation.id, MilestoneStatus.VERIFIED, ActorRole.SUPERVISOR
    )
    await add_recipient(db_session, user_id=funded.contractor.id)
    return funded


async def dispute(client: AsyncClient, milestone: Milestone, user: User, reason: str = "Cracks") -> Response:
    return await client.post(
        f"/api/v1/milestones/{milestone.id}/disputes", json={"reason": reason}, headers=bearer(user)
    )


async def resolve(
    client: AsyncClient, dispute_id: str, ops: User, outcome: str, key: str | None = None
) -> Response:
    headers = bearer(ops) | ({"Idempotency-Key": key} if key else {})
    return await client.post(
        f"/api/v1/disputes/{dispute_id}/resolve",
        json={"outcome": outcome, "notes": "Seen on site"},
        headers=headers,
    )


async def status_of(db_session: AsyncSession, milestone: Milestone) -> MilestoneStatus:
    await db_session.refresh(milestone)
    return milestone.status


# --- raising ----------------------------------------------------------------------------------


async def test_client_disputes_a_verified_milestone(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await verified(db_session)
    response = await dispute(client, funded.foundation, funded.client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["status"], body["raised_by"], body["reason"]) == ("open", str(funded.client.id), "Cracks")
    assert await status_of(db_session, funded.foundation) == MilestoneStatus.DISPUTED
    actions = [e.action for e in await audit_entries(db_session, uuid.UUID(body["id"]))]
    assert actions == ["dispute.opened"]
    assert [d.id for d in await escrow.list_open_disputes(db_session)] == [uuid.UUID(body["id"])]


async def test_contractor_cannot_dispute_yet(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await verified(db_session)
    response = await dispute(client, funded.foundation, funded.contractor)
    assert (response.status_code, response.json()["error"]["code"]) == (403, "dispute_not_allowed")


async def test_another_client_cannot_dispute(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await verified(db_session)
    stranger = await make_user(db_session, "client")
    response = await dispute(client, funded.foundation, stranger)
    assert (response.status_code, response.json()["error"]["code"]) == (403, "not_project_member")


async def test_only_a_verified_milestone_can_be_disputed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    funded = await make_active_project(db_session)
    response = await dispute(client, funded.foundation, funded.client)  # still pending
    assert (response.status_code, response.json()["error"]["code"]) == (409, "milestone_not_verified")


async def test_a_second_open_dispute_is_refused(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await verified(db_session)
    assert (await dispute(client, funded.foundation, funded.client)).status_code == 201
    again = await dispute(client, funded.foundation, funded.client)
    assert (again.status_code, again.json()["error"]["code"]) == (409, "dispute_already_open")


async def test_short_reason_is_422(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await verified(db_session)
    assert (await dispute(client, funded.foundation, funded.client, reason="x")).status_code == 422


async def test_no_release_while_a_dispute_is_open(
    client: AsyncClient, db_session: AsyncSession, queued: Queued
) -> None:
    funded = await verified(db_session)
    assert (await dispute(client, funded.foundation, funded.client)).status_code == 201
    with pytest.raises(AppError) as err:
        await escrow.request_release(db_session, funded.foundation.id, funded.client)
    assert (err.value.code, err.value.status_code) == ("dispute_open", 409)
    assert queued.releases == []


# --- resolving --------------------------------------------------------------------------------


async def test_rework_needs_two_different_ops_users(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await verified(db_session)
    dispute_id = (await dispute(client, funded.foundation, funded.client)).json()["id"]
    ops_a, ops_b = await make_user(db_session, "ops"), await make_user(db_session, "ops")

    first = await resolve(client, dispute_id, ops_a, "rework")
    assert first.status_code == 200, first.text
    assert first.json()["resolved"] is False
    assert first.json()["dispute"]["proposed_by"] == str(ops_a.id)
    assert await status_of(db_session, funded.foundation) == MilestoneStatus.DISPUTED

    same = await resolve(client, dispute_id, ops_a, "rework")
    assert (same.status_code, same.json()["error"]["code"]) == (409, "second_approval_required")
    other = await resolve(client, dispute_id, ops_b, "release")
    assert (other.status_code, other.json()["error"]["code"]) == (409, "resolution_mismatch")

    second = await resolve(client, dispute_id, ops_b, "rework")
    assert second.status_code == 200, second.text
    body = second.json()
    assert (body["resolved"], body["release_id"]) == (True, None)
    assert (body["dispute"]["status"], body["dispute"]["resolved_by"]) == ("resolved_reject", str(ops_b.id))
    assert await status_of(db_session, funded.foundation) == MilestoneStatus.FUNDED  # contractor reworks

    done = await resolve(client, dispute_id, ops_a, "rework")
    assert (done.status_code, done.json()["error"]["code"]) == (409, "dispute_not_open")
    assert await escrow.list_open_disputes(db_session) == []


async def test_resolved_for_release_pays_the_contractor(
    client: AsyncClient, db_session: AsyncSession, queued: Queued
) -> None:
    funded = await verified(db_session)
    dispute_id = (await dispute(client, funded.foundation, funded.client)).json()["id"]
    ops_a, ops_b = await make_user(db_session, "ops"), await make_user(db_session, "ops")
    assert (await resolve(client, dispute_id, ops_a, "release")).status_code == 200
    second = await resolve(client, dispute_id, ops_b, "release")
    assert second.status_code == 200, second.text
    release_id = uuid.UUID(second.json()["release_id"])
    assert second.json()["dispute"]["status"] == "resolved_release"
    assert queued.releases == [release_id]
    # Not released until escrow confirms: `released` always means the money moved.
    assert await status_of(db_session, funded.foundation) == MilestoneStatus.DISPUTED

    assert await escrow_tasks.run_submit_release(session_factory(db_session), release_id, retries=0) == "done"
    assert await status_of(db_session, funded.foundation) == MilestoneStatus.RELEASED
    assert await balance(db_session, accounts.contractor_payable("NGN")) == FOUNDATION_NGN
    released = [
        e for e in await audit_entries(db_session, funded.foundation.id) if e.action == "milestone.released"
    ]
    assert released[-1].actor_id == ops_b.id and released[-1].after is not None
    assert released[-1].after["actor_role"] == "ops"


async def test_resolve_needs_ops(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await verified(db_session)
    dispute_id = (await dispute(client, funded.foundation, funded.client)).json()["id"]
    response = await resolve(client, dispute_id, funded.client, "release")
    assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden_role")


async def test_unknown_dispute_is_404(client: AsyncClient, db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    assert (await resolve(client, str(uuid.uuid4()), ops, "rework")).status_code == 404


async def test_resolve_retry_with_the_same_key_replays(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await verified(db_session)
    dispute_id = (await dispute(client, funded.foundation, funded.client)).json()["id"]
    ops = await make_user(db_session, "ops")
    first = await resolve(client, dispute_id, ops, "rework", key="resolve-1")
    again = await resolve(client, dispute_id, ops, "rework", key="resolve-1")
    assert again.status_code == 200 and again.json() == first.json()  # not a second-approval error
