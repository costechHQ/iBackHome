"""Contractor matching: request, shortlist, choose, cancel (ADR 0007, phase 2). Needs Postgres."""

import json
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.notifications.adapters import FakeAdapter
from app.base.notifications.models import Channel, Notification
from app.base.users.models import User
from app.core.errors import AppError
from app.features.contractors import applications, match_notices
from app.features.contractors.models import ContractorProfile, MatchRequest, MatchShortlist
from app.features.contractors.tests.factories import (
    MATCH_URL,
    bearer,
    brief,
    make_contractor,
    make_project,
    make_user,
)
from app.features.projects import service as projects
from app.features.projects.models import Project

Queued = dict[str, list[Any]]


@pytest.fixture
async def ops(db_session: AsyncSession) -> User:
    return await make_user(db_session, "ops")


@pytest.fixture
async def client_user(db_session: AsyncSession) -> User:
    return await make_user(db_session, "client")


@pytest.fixture
async def project(db_session: AsyncSession, client_user: User) -> Project:
    return await make_project(db_session, client_user)


@pytest.fixture(autouse=True)
def _queued(monkeypatch: pytest.MonkeyPatch) -> Queued:
    """No Celery in tests: record what would be queued."""
    queued: Queued = {"ops_email": [], "notices": [], "decision": []}
    monkeypatch.setattr(match_notices, "enqueue_ops_email", lambda rid: queued["ops_email"].append(rid))
    monkeypatch.setattr(
        match_notices, "enqueue_notice", lambda rid, kind: queued["notices"].append((rid, kind))
    )
    monkeypatch.setattr(applications, "enqueue_decision_email", lambda rid: queued["decision"].append(rid))
    monkeypatch.setattr(applications, "enqueue_intake_emails", lambda rid: None)
    return queued


def ask_url(project: Project) -> str:
    return f"/api/v1/projects/{project.id}/match-request"


async def ask(client: AsyncClient, project: Project, who: User, **changes: Any) -> dict[str, Any]:
    response = await client.post(ask_url(project), json=brief(**changes), headers=bearer(who))
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def shortlisted(
    client: AsyncClient, request_id: str, ops: User, *profiles: ContractorProfile
) -> dict[str, Any]:
    response = await client.post(
        f"{MATCH_URL}/{request_id}/shortlist",
        json={"contractor_ids": [str(p.id) for p in profiles]},
        headers=bearer(ops),
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def choose(client: AsyncClient, request_id: str, who: User, profile: ContractorProfile) -> Any:
    return await client.post(
        f"{MATCH_URL}/{request_id}/choose", json={"contractor_id": str(profile.id)}, headers=bearer(who)
    )


# Asking


async def test_a_client_asks_and_the_budget_comes_from_the_project(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, _queued: Queued
) -> None:
    body = await ask(client, project, client_user)
    assert body["status"] == "open"
    assert (body["state"], body["city"], body["work_type"]) == ("Enugu", "Enugu", "buildings")
    assert (body["budget_minor"], body["currency"]) == (30_000_000_00, "NGN")
    assert body["shortlist"] == [] and body["chosen"] is None
    row = await db_session.get(MatchRequest, uuid.UUID(body["id"]))
    assert row is not None and row.client_id == client_user.id
    assert _queued["ops_email"] == [row.id]  # ops are emailed once the transaction commits


async def test_the_brief_cannot_set_the_budget_or_carry_extra_fields(
    client: AsyncClient, client_user: User, project: Project
) -> None:
    response = await client.post(ask_url(project), json=brief(budget_minor=1), headers=bearer(client_user))
    assert response.status_code == 422


@pytest.mark.parametrize(
    "changes", [{"work_type": "plumbing"}, {"state": "E"}, {"timeline": " "}, {"notes": "x" * 2001}]
)
async def test_a_bad_brief_is_422(
    client: AsyncClient, client_user: User, project: Project, changes: dict[str, Any]
) -> None:
    response = await client.post(ask_url(project), json=brief(**changes), headers=bearer(client_user))
    assert response.status_code == 422


async def test_only_this_projects_client_can_ask(
    client: AsyncClient, db_session: AsyncSession, project: Project, ops: User
) -> None:
    other_client = await make_user(db_session, "client")
    contractor = await make_user(db_session, "contractor")
    assert (await client.post(ask_url(project), json=brief())).status_code == 401
    refused = await client.post(ask_url(project), json=brief(), headers=bearer(other_client))
    assert (refused.status_code, refused.json()["error"]["code"]) == (403, "not_project_member")
    for wrong in (ops, contractor):
        assert (await client.post(ask_url(project), json=brief(), headers=bearer(wrong))).status_code == 403


async def test_a_project_with_a_contractor_cannot_ask(
    client: AsyncClient, db_session: AsyncSession, client_user: User
) -> None:
    with_contractor = await make_project(db_session, client_user, contractor_phone="08031112222")
    response = await client.post(ask_url(with_contractor), json=brief(), headers=bearer(client_user))
    assert (response.status_code, response.json()["error"]["code"]) == (409, "project_has_contractor")


async def test_a_project_past_draft_cannot_ask(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project
) -> None:
    project.status = "boq_review"
    await db_session.flush()
    response = await client.post(ask_url(project), json=brief(), headers=bearer(client_user))
    assert (response.status_code, response.json()["error"]["code"]) == (409, "project_not_draft")


async def test_one_active_request_per_project(
    client: AsyncClient, client_user: User, project: Project
) -> None:
    await ask(client, project, client_user)
    again = await client.post(ask_url(project), json=brief(), headers=bearer(client_user))
    assert (again.status_code, again.json()["error"]["code"]) == (409, "match_request_exists")


async def test_a_new_request_is_allowed_after_a_cancelled_one(
    client: AsyncClient, client_user: User, project: Project
) -> None:
    first = await ask(client, project, client_user)
    await client.post(f"{MATCH_URL}/{first['id']}/cancel", json={}, headers=bearer(client_user))
    second = await ask(client, project, client_user, city="Nsukka")
    assert second["id"] != first["id"]


async def test_the_same_idempotency_key_returns_the_first_answer(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project
) -> None:
    headers = {**bearer(client_user), "Idempotency-Key": "ask-1"}
    first = await client.post(ask_url(project), json=brief(), headers=headers)
    second = await client.post(ask_url(project), json=brief(), headers=headers)
    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json() == second.json()
    assert await db_session.scalar(select(func.count()).select_from(MatchRequest)) == 1


# Reading


async def test_the_client_and_ops_can_read_it_and_nobody_else(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    for who in (client_user, ops):
        shown = await client.get(ask_url(project), headers=bearer(who))
        assert shown.status_code == 200 and shown.json()["id"] == created["id"]
    other_client = await make_user(db_session, "client")
    assert (await client.get(ask_url(project), headers=bearer(other_client))).status_code == 403
    assert (await client.get(ask_url(project))).status_code == 401


async def test_no_request_yet_is_404(client: AsyncClient, client_user: User, project: Project) -> None:
    response = await client.get(ask_url(project), headers=bearer(client_user))
    assert (response.status_code, response.json()["error"]["code"]) == (404, "match_request_not_found")


async def test_the_ops_queue_lists_open_requests_oldest_first_with_the_project_title(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    first_client = await make_user(db_session, "client")
    second_client = await make_user(db_session, "client")
    first = await ask(client, await make_project(db_session, first_client), first_client)
    second = await ask(client, await make_project(db_session, second_client), second_client)
    older = await db_session.get(MatchRequest, uuid.UUID(first["id"]))
    assert older is not None
    older.created_at = older.created_at.replace(year=2026, month=1)
    await db_session.flush()

    listed = (await client.get("/api/v1/ops/match-requests", headers=bearer(ops))).json()
    assert [i["id"] for i in listed["items"]] == [first["id"], second["id"]]
    assert listed["items"][0]["project_title"] == "3-bedroom bungalow"
    assert listed["items"][0]["shortlist_count"] == 0
    page = (await client.get("/api/v1/ops/match-requests?limit=1", headers=bearer(ops))).json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    assert (await client.get("/api/v1/ops/match-requests", headers=bearer(first_client))).status_code == 403


# Shortlisting


async def test_ops_shortlist_and_the_client_sees_safe_cards_and_is_told(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User,
    project: Project,
    ops: User,
    _queued: Queued,
) -> None:
    created = await ask(client, project, client_user)
    first = await make_contractor(db_session, ops, business_name="Obi Works", phone="08031234567")
    second = await make_contractor(db_session, ops, business_name="Eze Builders")
    body = await shortlisted(client, created["id"], ops, second, first)
    assert body["status"] == "shortlisted"
    assert [c["business_name"] for c in body["shortlist"]] == ["Eze Builders", "Obi Works"]  # ops' order
    assert _queued["notices"] == [(uuid.UUID(created["id"]), "shortlist")]

    # What the client sees: no phone, email, user id or references anywhere.
    as_client = (await client.get(ask_url(project), headers=bearer(client_user))).text
    for secret in ("+2348031234567", "@example.com", str(first.user_id), "reference", "RC1234567"):
        assert secret not in as_client
    card = json.loads(as_client)["shortlist"][0]
    assert set(card) == {
        "id",
        "business_name",
        "summary",
        "states_served",
        "specialties",
        "years_in_business",
        "projects_completed",
        "vetted_by_ibackhome",
    }


async def test_only_ops_can_shortlist(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    payload = {"contractor_ids": [str(profile.id)]}
    url = f"{MATCH_URL}/{created['id']}/shortlist"
    assert (await client.post(url, json=payload)).status_code == 401
    assert (await client.post(url, json=payload, headers=bearer(client_user))).status_code == 403


@pytest.mark.parametrize("count", [0, 4])
async def test_a_shortlist_has_one_to_three_contractors(
    client: AsyncClient, client_user: User, project: Project, ops: User, count: int
) -> None:
    created = await ask(client, project, client_user)
    ids = [str(uuid.uuid4()) for _ in range(count)]
    response = await client.post(
        f"{MATCH_URL}/{created['id']}/shortlist", json={"contractor_ids": ids}, headers=bearer(ops)
    )
    assert response.status_code == 422


async def test_a_contractor_cannot_be_listed_twice(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    response = await client.post(
        f"{MATCH_URL}/{created['id']}/shortlist",
        json={"contractor_ids": [str(profile.id), str(profile.id)]},
        headers=bearer(ops),
    )
    assert response.status_code == 422


@pytest.mark.parametrize("problem", ["unlisted", "suspended_profile", "suspended_user", "unknown"])
async def test_only_approved_listed_active_contractors_can_be_shortlisted(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User,
    project: Project,
    ops: User,
    problem: str,
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    target = str(profile.id)
    if problem == "unlisted":
        profile.listed = False
    elif problem == "suspended_profile":
        profile.vetting_status = "suspended"
    elif problem == "suspended_user":
        user = await db_session.get(User, profile.user_id)
        assert user is not None
        user.status = "suspended"
    else:
        target = str(uuid.uuid4())
    await db_session.flush()
    response = await client.post(
        f"{MATCH_URL}/{created['id']}/shortlist", json={"contractor_ids": [target]}, headers=bearer(ops)
    )
    assert (response.status_code, response.json()["error"]["code"]) == (422, "contractor_not_available")
    row = await db_session.get(MatchRequest, uuid.UUID(created["id"]))
    assert row is not None and row.status == "open"


async def test_ops_can_replace_the_shortlist_and_the_client_is_told_again(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User,
    project: Project,
    ops: User,
    _queued: Queued,
) -> None:
    created = await ask(client, project, client_user)
    first = await make_contractor(db_session, ops)
    second = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, first)
    body = await shortlisted(client, created["id"], ops, second)
    assert [c["id"] for c in body["shortlist"]] == [str(second.id)]
    assert await db_session.scalar(select(func.count()).select_from(MatchShortlist)) == 1
    row = await db_session.get(MatchRequest, uuid.UUID(created["id"]))
    assert row is not None and row.shortlist_version == 2
    assert [kind for _, kind in _queued["notices"]] == ["shortlist", "shortlist"]


async def test_a_decided_request_cannot_be_shortlisted(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    await client.post(f"{MATCH_URL}/{created['id']}/cancel", json={}, headers=bearer(ops))
    response = await client.post(
        f"{MATCH_URL}/{created['id']}/shortlist",
        json={"contractor_ids": [str(profile.id)]},
        headers=bearer(ops),
    )
    assert (response.status_code, response.json()["error"]["code"]) == (409, "invalid_transition")


async def test_a_project_that_moved_on_cannot_be_shortlisted(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    project.status = "boq_review"
    await db_session.flush()
    response = await client.post(
        f"{MATCH_URL}/{created['id']}/shortlist",
        json={"contractor_ids": [str(profile.id)]},
        headers=bearer(ops),
    )
    assert (response.status_code, response.json()["error"]["code"]) == (409, "project_not_draft")


# Choosing


async def test_the_client_chooses_and_the_contractor_is_set_and_told(
    client: AsyncClient,
    db_session: AsyncSession,
    client_user: User,
    project: Project,
    ops: User,
    _queued: Queued,
) -> None:
    created = await ask(client, project, client_user)
    first = await make_contractor(db_session, ops)
    second = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, first, second)
    response = await choose(client, created["id"], client_user, second)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "matched"
    assert body["chosen"]["id"] == str(second.id)
    assert body["decided_at"]

    await db_session.refresh(project)
    assert project.contractor_id == second.user_id  # the project's contractor, as if invited at creation
    row = await db_session.get(MatchRequest, uuid.UUID(created["id"]))
    assert row is not None and row.chosen_contractor_id == second.user_id
    assert (uuid.UUID(created["id"]), "chosen") in _queued["notices"]
    # The audit trail has the match and the contractor being set on the project.
    actions = set(
        await db_session.scalars(select(AuditEntry.action).where(AuditEntry.actor_id == client_user.id))
    )
    assert {"match_request.created", "match_request.matched", "project.contractor_set"} <= actions


async def test_only_the_owner_can_choose(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, profile)
    url, payload = f"{MATCH_URL}/{created['id']}/choose", {"contractor_id": str(profile.id)}
    other_client = await make_user(db_session, "client")
    assert (await client.post(url, json=payload)).status_code == 401
    assert (await client.post(url, json=payload, headers=bearer(ops))).status_code == 403
    not_theirs = await client.post(url, json=payload, headers=bearer(other_client))
    assert (not_theirs.status_code, not_theirs.json()["error"]["code"]) == (404, "match_request_not_found")


async def test_a_contractor_not_on_the_shortlist_is_refused(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    listed = await make_contractor(db_session, ops)
    other = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, listed)
    response = await choose(client, created["id"], client_user, other)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "contractor_not_on_shortlist")


async def test_choosing_before_a_shortlist_exists_is_refused(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    response = await choose(client, created["id"], client_user, profile)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "invalid_transition")


async def test_a_contractor_who_became_unavailable_cannot_be_chosen(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, profile)
    profile.listed = False
    await db_session.flush()
    response = await choose(client, created["id"], client_user, profile)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "contractor_not_available")
    await db_session.refresh(project)
    assert project.contractor_id is None


async def test_a_second_choice_is_refused_and_changes_nothing(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    first = await make_contractor(db_session, ops)
    second = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, first, second)
    assert (await choose(client, created["id"], client_user, first)).status_code == 200
    again = await choose(client, created["id"], client_user, second)
    assert (again.status_code, again.json()["error"]["code"]) == (409, "invalid_transition")
    await db_session.refresh(project)
    assert project.contractor_id == first.user_id


async def test_the_chosen_contractor_then_works_on_the_project(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, profile)
    await choose(client, created["id"], client_user, profile)
    contractor = await db_session.get(User, profile.user_id)
    assert contractor is not None
    shown = await client.get(f"/api/v1/projects/{project.id}", headers=bearer(contractor))  # now a member
    assert shown.status_code == 200
    assert shown.json()["contractor"]["id"] == str(contractor.id)


# Cancelling


async def test_the_client_or_ops_can_cancel_and_a_decided_one_cannot(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    url = f"{MATCH_URL}/{created['id']}/cancel"
    other_client = await make_user(db_session, "client")
    hidden = await client.post(url, json={}, headers=bearer(other_client))
    assert (hidden.status_code, hidden.json()["error"]["code"]) == (404, "match_request_not_found")

    done = await client.post(url, json={"reason": "Found one myself."}, headers=bearer(client_user))
    assert done.status_code == 200
    assert (done.json()["status"], done.json()["cancel_reason"]) == ("cancelled", "Found one myself.")
    again = await client.post(url, json={}, headers=bearer(ops))
    assert (again.status_code, again.json()["error"]["code"]) == (409, "invalid_transition")


async def test_ops_can_cancel_a_shortlisted_request(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, profile)
    response = await client.post(f"{MATCH_URL}/{created['id']}/cancel", json={}, headers=bearer(ops))
    assert response.status_code == 200 and response.json()["status"] == "cancelled"


async def test_a_matched_request_cannot_be_cancelled(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, profile)
    await choose(client, created["id"], client_user, profile)
    response = await client.post(f"{MATCH_URL}/{created['id']}/cancel", json={}, headers=bearer(client_user))
    assert (response.status_code, response.json()["error"]["code"]) == (409, "invalid_transition")


# The messages


async def test_ops_are_emailed_the_brief_once(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project
) -> None:
    created = await ask(client, project, client_user)
    email = FakeAdapter()
    rid = uuid.UUID(created["id"])
    assert await match_notices.send_ops_email(db_session, rid, adapters={Channel.EMAIL: email}) is True
    assert await match_notices.send_ops_email(db_session, rid, adapters={Channel.EMAIL: email}) is True
    ((to, message),) = email.sent  # the repeat sent nothing
    assert to == "ops@ibackhome.com"
    for expected in (
        "3-bedroom bungalow",
        "5 Zik Avenue, Enugu",
        "NGN 30,000,000.00",
        "Enugu, Enugu",
        "buildings",
    ):
        assert expected in message.text
    assert "Phone each contractor" in message.text


async def test_an_email_outage_returns_false_to_retry(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project
) -> None:
    created = await ask(client, project, client_user)
    rid = uuid.UUID(created["id"])
    assert (
        await match_notices.send_ops_email(db_session, rid, adapters={Channel.EMAIL: FakeAdapter(fail=True)})
        is False
    )
    assert await match_notices.send_ops_email(db_session, rid, adapters={}) is False


async def test_the_client_and_the_contractor_are_each_told_once(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    rid = uuid.UUID(created["id"])
    adapters = {channel: FakeAdapter() for channel in Channel}

    await shortlisted(client, created["id"], ops, profile)
    await match_notices.send_notice(db_session, rid, "shortlist", adapters=adapters)
    await match_notices.send_notice(db_session, rid, "shortlist", adapters=adapters)  # a repeat sends nothing
    sent = list(await db_session.scalars(select(Notification).where(Notification.user_id == client_user.id)))
    assert [n.template for n in sent] == ["match_request.shortlist_ready"]

    await choose(client, created["id"], client_user, profile)
    await match_notices.send_notice(db_session, rid, "chosen", adapters=adapters)
    await match_notices.send_notice(db_session, rid, "chosen", adapters=adapters)
    told = list(await db_session.scalars(select(Notification).where(Notification.user_id == profile.user_id)))
    assert [n.template for n in told] == ["match_request.contractor_chosen"]


async def test_a_cancelled_request_sends_no_shortlist_message(
    client: AsyncClient, db_session: AsyncSession, client_user: User, project: Project, ops: User
) -> None:
    created = await ask(client, project, client_user)
    profile = await make_contractor(db_session, ops)
    await shortlisted(client, created["id"], ops, profile)
    await client.post(f"{MATCH_URL}/{created['id']}/cancel", json={}, headers=bearer(client_user))
    adapters = {channel: FakeAdapter() for channel in Channel}
    await match_notices.send_notice(db_session, uuid.UUID(created["id"]), "shortlist", adapters=adapters)
    assert await db_session.scalar(select(func.count()).select_from(Notification)) == 0


# projects.set_contractor


async def test_set_contractor_is_for_draft_projects_without_one(
    db_session: AsyncSession, client_user: User, project: Project
) -> None:
    first = await make_user(db_session, "contractor")
    second = await make_user(db_session, "contractor")
    updated = await projects.set_contractor(db_session, project.id, first.id, client_user.id)
    assert updated.contractor_id == first.id
    same = await projects.set_contractor(db_session, project.id, first.id, client_user.id)
    assert same.contractor_id == first.id  # the same contractor again changes nothing
    with pytest.raises(AppError) as taken:
        await projects.set_contractor(db_session, project.id, second.id, client_user.id)
    assert taken.value.code == "project_has_contractor"


async def test_set_contractor_refuses_other_roles_suspended_users_and_started_projects(
    db_session: AsyncSession, client_user: User, project: Project
) -> None:
    not_contractor = await make_user(db_session, "supervisor")
    with pytest.raises(AppError) as wrong_role:
        await projects.set_contractor(db_session, project.id, not_contractor.id, client_user.id)
    assert wrong_role.value.code == "not_a_contractor"

    suspended = await make_user(db_session, "contractor")
    suspended.status = "suspended"
    await db_session.flush()
    with pytest.raises(AppError) as banned:
        await projects.set_contractor(db_session, project.id, suspended.id, client_user.id)
    assert banned.value.code == "contractor_suspended"

    contractor = await make_user(db_session, "contractor")
    project.status = "boq_review"
    await db_session.flush()
    with pytest.raises(AppError) as started:
        await projects.set_contractor(db_session, project.id, contractor.id, client_user.id)
    assert started.value.code == "project_not_draft"

    with pytest.raises(AppError) as missing:
        await projects.set_contractor(db_session, project.id, uuid.uuid4(), client_user.id)
    assert missing.value.code == "user_not_found"
