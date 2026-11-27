"""Ops vetting of contractor applications and the directory (ADR 0007, phase 1). Needs Postgres."""

import json
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.notifications.adapters import FakeAdapter
from app.base.notifications.models import Channel
from app.base.users.models import User
from app.features.contractors import applications, service
from app.features.contractors.models import ContractorApplication, ContractorProfile
from app.features.contractors.schemas import ContractorDecisionIn
from app.features.contractors.tests.factories import (
    URL,
    approval,
    bearer,
    form,
    make_application,
    make_user,
)


@pytest.fixture
async def ops(db_session: AsyncSession) -> User:
    return await make_user(db_session, "ops")


@pytest.fixture(autouse=True)
def _queued(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    """No Celery in tests: record which decision emails would be queued."""
    queued: list[uuid.UUID] = []
    monkeypatch.setattr(applications, "enqueue_decision_email", queued.append)
    monkeypatch.setattr(applications, "enqueue_intake_emails", lambda _id: None)
    return queued


def decide(application_id: uuid.UUID) -> str:
    return f"{URL}/{application_id}/decision"


async def profiles(db_session: AsyncSession) -> int:
    return int(await db_session.scalar(select(func.count()).select_from(ContractorProfile)) or 0)


# Who may


async def test_only_ops_can_vet(client: AsyncClient, db_session: AsyncSession, ops: User) -> None:
    row = await make_application(db_session)
    client_user = await make_user(db_session, "client")
    for url in (URL, f"{URL}/{row.id}", "/api/v1/contractors"):
        assert (await client.get(url)).status_code == 401
        assert (await client.get(url, headers=bearer(client_user))).status_code == 403
    assert (await client.post(decide(row.id), json=approval())).status_code == 401
    assert (
        await client.post(decide(row.id), json=approval(), headers=bearer(client_user))
    ).status_code == 403
    assert (await client.get(URL, headers=bearer(ops))).status_code == 200


# The queue


async def test_the_queue_lists_pending_oldest_first_and_pages(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    first = await make_application(db_session, business_name="First Ltd")
    second = await make_application(db_session, business_name="Second Ltd")
    third = await make_application(db_session, business_name="Third Ltd")
    first.created_at = first.created_at.replace(year=2026, month=1)
    second.created_at = second.created_at.replace(year=2026, month=2)
    await db_session.flush()

    page1 = (await client.get(f"{URL}?limit=2", headers=bearer(ops))).json()
    assert [i["business_name"] for i in page1["items"]] == ["First Ltd", "Second Ltd"]
    assert page1["next_cursor"]
    page2 = (await client.get(f"{URL}?limit=2&cursor={page1['next_cursor']}", headers=bearer(ops))).json()
    assert [i["id"] for i in page2["items"]] == [str(third.id)]
    assert page2["next_cursor"] is None
    # The list shows no phone, email or references: those are in the single application.
    assert "phone" not in page1["items"][0]


async def test_the_queue_filters_by_status(client: AsyncClient, db_session: AsyncSession, ops: User) -> None:
    row = await make_application(db_session)
    assert (await client.post(decide(row.id), json=approval(), headers=bearer(ops))).status_code == 200
    assert (await client.get(URL, headers=bearer(ops))).json()["items"] == []
    done = (await client.get(f"{URL}?status=approved", headers=bearer(ops))).json()["items"]
    assert [i["id"] for i in done] == [str(row.id)]
    assert (await client.get(f"{URL}?status=bogus", headers=bearer(ops))).status_code == 422


async def test_one_application_is_shown_in_full(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    row = await make_application(db_session)
    shown = (await client.get(f"{URL}/{row.id}", headers=bearer(ops))).json()
    assert shown["phone"] == row.phone
    assert shown["reference_1_phone"] == row.reference_1_phone
    assert shown["cac_rc_number"] == "RC1234567"
    assert shown["status"] == "pending"
    assert (await client.get(f"{URL}/{uuid.uuid4()}", headers=bearer(ops))).status_code == 404


# Approving


async def test_approval_creates_the_contractor_user_and_profile_and_queues_the_email(
    client: AsyncClient, db_session: AsyncSession, ops: User, _queued: list[uuid.UUID]
) -> None:
    row = await make_application(db_session, phone="08031234567")
    response = await client.post(decide(row.id), json=approval(), headers=bearer(ops))
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    await db_session.refresh(row)
    assert (row.decided_by, row.registration_verified, row.reference_1_verified) == (ops.id, True, True)
    assert row.ops_notes and "CAC register" in row.ops_notes

    user = await db_session.scalar(select(User).where(User.phone == "+2348031234567"))
    assert user is not None
    assert user.role == "contractor"
    profile = await db_session.scalar(select(ContractorProfile).where(ContractorProfile.user_id == user.id))
    assert profile is not None
    assert profile.business_name == "Obi Building Works"
    assert profile.summary.startswith("Established Enugu builder")  # exactly what ops wrote
    assert (profile.states_served, profile.specialties) == (["Enugu", "Anambra"], ["buildings", "roofing"])
    assert (profile.vetting_status, profile.listed, profile.vetted_by) == ("approved", True, ops.id)
    assert profile.application_id == row.id
    assert _queued == [row.id]


async def test_an_invited_contractor_is_reused_not_duplicated(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    existing = await make_user(db_session, "contractor", "+2348031234567")  # invited earlier by a client
    row = await make_application(db_session, phone="08031234567")
    assert (await client.post(decide(row.id), json=approval(), headers=bearer(ops))).status_code == 200
    profile = await db_session.scalar(select(ContractorProfile))
    assert profile is not None and profile.user_id == existing.id


async def test_approval_needs_both_references_ticked(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    row = await make_application(db_session)
    response = await client.post(
        decide(row.id), json=approval(reference_2_verified=False), headers=bearer(ops)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "vetting_checks_incomplete"
    assert "reference 2" in response.json()["error"]["message"]
    assert await profiles(db_session) == 0
    await db_session.refresh(row)
    assert row.status == "pending"


async def test_the_registration_is_needed_only_when_a_number_was_given(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    with_number = await make_application(db_session, cac_rc_number="RC1234567")
    refused = await client.post(
        decide(with_number.id), json=approval(registration_verified=False), headers=bearer(ops)
    )
    assert refused.status_code == 422
    assert "registration" in refused.json()["error"]["message"]

    without = await make_application(db_session, cac_rc_number=None, corbon_number=None)
    accepted = await client.post(
        decide(without.id), json=approval(registration_verified=False), headers=bearer(ops)
    )
    assert accepted.status_code == 200


@pytest.mark.parametrize("summary", [None, "", "too short"])
async def test_approval_needs_a_profile_summary_written_by_ops(
    client: AsyncClient, db_session: AsyncSession, ops: User, summary: str | None
) -> None:
    row = await make_application(db_session)
    response = await client.post(decide(row.id), json=approval(summary=summary), headers=bearer(ops))
    assert response.status_code == 422
    assert await profiles(db_session) == 0


async def test_a_number_that_belongs_to_another_role_is_refused_and_nothing_changes(
    client: AsyncClient, db_session: AsyncSession, ops: User, _queued: list[uuid.UUID]
) -> None:
    await make_user(db_session, "client", "+2348031234567")
    row = await make_application(db_session, phone="08031234567")
    response = await client.post(decide(row.id), json=approval(), headers=bearer(ops))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "role_conflict"
    await db_session.refresh(row)
    assert row.status == "pending" and row.decided_by is None
    assert await profiles(db_session) == 0
    assert _queued == []
    role = await db_session.scalar(select(User.role).where(User.phone == "+2348031234567"))
    assert role == "client"  # never changed by an approval


# Rejecting and deciding twice


async def test_rejection_needs_a_reason_and_creates_no_account(
    client: AsyncClient, db_session: AsyncSession, ops: User, _queued: list[uuid.UUID]
) -> None:
    row = await make_application(db_session, phone="08031234567")
    assert (
        await client.post(decide(row.id), json={"decision": "rejected"}, headers=bearer(ops))
    ).status_code == 422

    response = await client.post(
        decide(row.id),
        json={"decision": "rejected", "reason": "We could not verify the RC number."},
        headers=bearer(ops),
    )
    assert response.status_code == 200
    await db_session.refresh(row)
    assert (row.status, row.rejection_reason) == ("rejected", "We could not verify the RC number.")
    assert await profiles(db_session) == 0
    assert await db_session.scalar(select(User).where(User.phone == "+2348031234567")) is None
    assert _queued == [row.id]


async def test_a_rejected_applicant_may_apply_again(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    body = form(phone="08031234567", email="again@example.com")
    first = await client.post(URL, json=body)
    await client.post(
        decide(uuid.UUID(first.json()["id"])),
        json={"decision": "rejected", "reason": "Not yet."},
        headers=bearer(ops),
    )
    assert (await client.post(URL, json=body)).status_code == 201


async def test_an_application_is_decided_once(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    row = await make_application(db_session)
    assert (await client.post(decide(row.id), json=approval(), headers=bearer(ops))).status_code == 200
    again = await client.post(decide(row.id), json=approval(), headers=bearer(ops))
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "application_decided"
    assert await profiles(db_session) == 1


async def test_a_retried_decision_with_the_same_key_returns_the_first_answer(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    row = await make_application(db_session)
    headers = {**bearer(ops), "Idempotency-Key": "decide-1"}
    first = await client.post(decide(row.id), json=approval(), headers=headers)
    second = await client.post(decide(row.id), json=approval(), headers=headers)
    assert (first.status_code, second.status_code) == (200, 200)
    assert await profiles(db_session) == 1


async def test_an_unknown_application_is_404(client: AsyncClient, ops: User) -> None:
    response = await client.post(decide(uuid.uuid4()), json=approval(), headers=bearer(ops))
    assert response.status_code == 404


# Audit


async def test_decisions_are_audited_without_phone_numbers_or_emails(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    row = await make_application(db_session, phone="08031234567", email="private@example.com")
    await client.post(decide(row.id), json=approval(), headers=bearer(ops))
    entries = list(await db_session.scalars(select(AuditEntry).where(AuditEntry.actor_id == ops.id)))
    assert {e.action for e in entries} == {"contractor_application.approved", "contractor.approved"}
    dumped = json.dumps([[e.before, e.after] for e in entries])
    for secret in ("+2348031234567", "private@example.com", row.reference_1_phone, row.requested_ip):
        assert secret not in dumped  # the log is append-only: contact details never go in


# The decision email


async def test_the_applicant_is_told_the_decision_once(db_session: AsyncSession, ops: User) -> None:
    approved = await make_application(db_session, contact_name="Chinedu Obi", email="chinedu@example.com")
    rejected = await make_application(db_session, contact_name="Ada Eze", email="ada@example.com")
    await service.decide(db_session, approved.id, ContractorDecisionIn(**approval()), ops.id)
    await service.decide(
        db_session,
        rejected.id,
        ContractorDecisionIn(decision="rejected", reason="No valid registration."),
        ops.id,
    )
    email = FakeAdapter()
    adapters = {Channel.EMAIL: email}
    assert await applications.send_decision_email(db_session, approved.id, adapters=adapters) is True
    assert await applications.send_decision_email(db_session, approved.id, adapters=adapters) is True
    assert await applications.send_decision_email(db_session, rejected.id, adapters=adapters) is True
    assert len(email.sent) == 2  # the repeat sent nothing
    (to_ok, ok_msg), (to_no, no_msg) = email.sent
    assert to_ok == "chinedu@example.com" and "approved" in ok_msg.text
    assert to_no == "ada@example.com" and "No valid registration." in no_msg.text


async def test_a_decision_email_outage_returns_false_to_retry(db_session: AsyncSession, ops: User) -> None:
    row = await make_application(db_session)
    await service.decide(db_session, row.id, ContractorDecisionIn(**approval()), ops.id)
    assert (
        await applications.send_decision_email(
            db_session, row.id, adapters={Channel.EMAIL: FakeAdapter(fail=True)}
        )
        is False
    )
    assert row.decision_emailed_at is None


# The directory


async def approved_contractor(
    client: AsyncClient, db_session: AsyncSession, ops: User, **changes: Any
) -> ContractorApplication:
    row = await make_application(db_session, **changes)
    assert (await client.post(decide(row.id), json=approval(), headers=bearer(ops))).status_code == 200
    return row


async def test_the_directory_lists_approved_contractors_and_filters(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    await approved_contractor(
        client,
        db_session,
        ops,
        business_name="Enugu Roofers",
        states_served=["Enugu"],
        specialties=["roofing"],
    )
    await approved_contractor(
        client,
        db_session,
        ops,
        business_name="Lagos Builders",
        states_served=["Lagos"],
        specialties=["buildings"],
    )
    await make_application(db_session, business_name="Still Pending")  # not vetted: never listed

    everyone = (await client.get("/api/v1/contractors", headers=bearer(ops))).json()["items"]
    assert {c["business_name"] for c in everyone} == {"Enugu Roofers", "Lagos Builders"}
    assert "phone" not in everyone[0] and "email" not in everyone[0]

    by_state = (await client.get("/api/v1/contractors?state=Enugu", headers=bearer(ops))).json()["items"]
    assert [c["business_name"] for c in by_state] == ["Enugu Roofers"]
    by_specialty = (await client.get("/api/v1/contractors?specialty=buildings", headers=bearer(ops))).json()[
        "items"
    ]
    assert [c["business_name"] for c in by_specialty] == ["Lagos Builders"]
    both = (
        await client.get("/api/v1/contractors?state=Lagos&specialty=roofing", headers=bearer(ops))
    ).json()["items"]
    assert both == []


async def test_the_directory_can_filter_by_listed_and_pages(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    for name in ("A Ltd", "B Ltd", "C Ltd"):
        await approved_contractor(client, db_session, ops, business_name=name)
    hidden = await db_session.scalar(
        select(ContractorProfile).where(ContractorProfile.business_name == "B Ltd")
    )
    assert hidden is not None
    hidden.listed = False
    await db_session.flush()

    listed = (await client.get("/api/v1/contractors?listed=true", headers=bearer(ops))).json()["items"]
    assert {c["business_name"] for c in listed} == {"A Ltd", "C Ltd"}
    unlisted = (await client.get("/api/v1/contractors?listed=false", headers=bearer(ops))).json()["items"]
    assert [c["business_name"] for c in unlisted] == ["B Ltd"]

    page1 = (await client.get("/api/v1/contractors?limit=2", headers=bearer(ops))).json()
    assert len(page1["items"]) == 2 and page1["next_cursor"]
    page2 = (
        await client.get(f"/api/v1/contractors?limit=2&cursor={page1['next_cursor']}", headers=bearer(ops))
    ).json()
    assert len(page2["items"]) == 1 and page2["next_cursor"] is None
