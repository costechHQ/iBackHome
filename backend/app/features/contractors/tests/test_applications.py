"""The public contractor form: POST /contractor-applications (ADR 0007). Needs Postgres."""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications.adapters import FakeAdapter
from app.base.notifications.models import Channel
from app.features.contractors import applications
from app.features.contractors.models import ContractorApplication
from app.features.contractors.settings import get_contractor_settings
from app.features.contractors.tests.factories import URL, form, make_application


async def count(db_session: AsyncSession) -> int:
    return int(await db_session.scalar(select(func.count()).select_from(ContractorApplication)) or 0)


@pytest.fixture(autouse=True)
def _queued(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    """No Celery in tests: record what would be queued."""
    queued: list[uuid.UUID] = []
    monkeypatch.setattr(applications, "enqueue_intake_emails", queued.append)
    return queued


@pytest.fixture
def small_limit(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("CONTRACTOR_APPLICATION_LIMIT_PER_IP", "2")
    get_contractor_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_contractor_settings.cache_clear()


# Saving


async def test_a_public_application_is_saved_and_queued_after_commit(
    client: AsyncClient, db_session: AsyncSession, _queued: list[uuid.UUID]
) -> None:
    response = await client.post(
        URL, json=form(phone="08031234567", email="Obi@Example.com", states_served=["Enugu", "Enugu", "Imo"])
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    row = await db_session.get(ContractorApplication, uuid.UUID(body["id"]))
    assert row is not None
    assert row.phone == "+2348031234567"  # E.164, like login
    assert row.email == "obi@example.com"
    assert row.states_served == ["Enugu", "Imo"]  # no repeats
    assert row.specialties == ["buildings", "roofing"]
    assert (row.cac_rc_number, row.corbon_number) == ("RC1234567", None)
    assert row.status == "pending"
    assert row.requested_ip
    assert _queued == [row.id]  # the emails are queued once the transaction commits


async def test_no_login_is_needed(client: AsyncClient) -> None:
    assert (await client.post(URL, json=form())).status_code == 201  # no Authorization header


async def test_the_registration_numbers_are_optional(client: AsyncClient) -> None:
    assert (await client.post(URL, json=form(cac_rc_number=None, corbon_number=None))).status_code == 201


# What is refused


async def test_a_nin_is_refused_not_stored(client: AsyncClient, db_session: AsyncSession) -> None:
    response = await client.post(URL, json=form(nin="12345678901"))
    assert response.status_code == 422
    assert await count(db_session) == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"consent": False},
        {"specialties": ["plumbing"]},
        {"specialties": []},
        {"states_served": []},
        {"states_served": [f"State{i}" for i in range(11)]},
        {"states_served": ["E"]},
        {"years_in_business": -1},
        {"years_in_business": 81},
        {"projects_completed": 10_001},
        {"business_name": " "},
        {"cac_rc_number": "R"},
    ],
)
async def test_bad_fields_are_422(
    client: AsyncClient, db_session: AsyncSession, changes: dict[str, Any]
) -> None:
    assert (await client.post(URL, json=form(**changes))).status_code == 422
    assert await count(db_session) == 0


async def test_a_missing_field_is_422(client: AsyncClient) -> None:
    body = form()
    del body["reference_2_phone"]
    assert (await client.post(URL, json=body)).status_code == 422


async def test_an_email_in_the_phone_field_is_refused(client: AsyncClient) -> None:
    response = await client.post(URL, json=form(phone="obi@example.com"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_phone"


async def test_a_phone_in_the_email_field_is_refused(client: AsyncClient) -> None:
    response = await client.post(URL, json=form(email="08031234567"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_email"


async def test_the_two_references_must_differ(client: AsyncClient) -> None:
    response = await client.post(
        URL, json=form(reference_1_phone="08051111111", reference_2_phone="+2348051111111")
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "references_must_differ"


async def test_a_reference_cannot_be_the_applicant(client: AsyncClient) -> None:
    response = await client.post(URL, json=form(phone="08031111111", reference_1_phone="+2348031111111"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "reference_is_applicant"


# Duplicates, spam, retries


async def test_a_second_pending_application_for_the_same_phone_is_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await client.post(URL, json=form(phone="08032222222"))).status_code == 201
    again = await client.post(URL, json=form(phone="+2348032222222"))  # same number, other spelling
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "application_exists"
    assert await count(db_session) == 1


async def test_a_second_pending_application_for_the_same_email_is_409(client: AsyncClient) -> None:
    assert (await client.post(URL, json=form(email="same@example.com"))).status_code == 201
    assert (await client.post(URL, json=form(email="SAME@example.com"))).status_code == 409


async def test_too_many_from_one_ip_is_429(client: AsyncClient, small_limit: None) -> None:
    assert (await client.post(URL, json=form())).status_code == 201
    assert (await client.post(URL, json=form())).status_code == 201
    third = await client.post(URL, json=form())
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limited"
    assert int(third.headers["Retry-After"]) > 0


async def test_the_honeypot_looks_like_success_and_stores_nothing(
    client: AsyncClient, db_session: AsyncSession, _queued: list[uuid.UUID]
) -> None:
    response = await client.post(URL, json=form(website="http://spam.example"))
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert await count(db_session) == 0
    assert _queued == []


async def test_the_same_idempotency_key_returns_the_first_answer(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    body = form()
    headers = {"Idempotency-Key": "contractor-apply-1"}
    first = await client.post(URL, json=body, headers=headers)
    second = await client.post(URL, json=body, headers=headers)
    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json() == second.json()
    assert await count(db_session) == 1


# The emails


async def test_ops_get_every_detail_and_the_review_order_and_the_applicant_a_receipt(
    db_session: AsyncSession,
) -> None:
    row = await make_application(db_session, contact_name="Chinedu Obi", email="chinedu@example.com")
    email = FakeAdapter()
    assert await applications.send_emails(db_session, row.id, adapters={Channel.EMAIL: email}) is True
    (to_ops, ops_msg), (to_applicant, receipt) = email.sent
    assert to_ops == get_contractor_settings().ops_notify_email == "ops@ibackhome.com"
    for expected in (
        "Obi Building Works",
        row.phone,
        "Enugu, Anambra",
        "RC1234567",
        "Emeka Obi",
        str(row.id),
    ):
        assert expected in ops_msg.text
    assert "CORBON number: not given" in ops_msg.text
    first, second, third = (
        ops_msg.text.index(s) for s in ("1. Check the registration", "2. Call both", "3. Open")
    )
    assert first < second < third  # registration, then references, then decide
    assert to_applicant == "chinedu@example.com"
    assert receipt.text.startswith("Hello Chinedu,")
    assert "Obi Building Works" in receipt.text


async def test_each_email_goes_out_once(db_session: AsyncSession) -> None:
    row = await make_application(db_session)
    email = FakeAdapter()
    adapters = {Channel.EMAIL: email}
    await applications.send_emails(db_session, row.id, adapters=adapters)
    await applications.send_emails(db_session, row.id, adapters=adapters)
    assert len(email.sent) == 2  # one to ops, one receipt; the second run sends nothing


async def test_a_provider_outage_keeps_the_application_and_the_job_tries_again(
    db_session: AsyncSession,
) -> None:
    row = await make_application(db_session)
    down = FakeAdapter(fail=True)
    assert await applications.send_emails(db_session, row.id, adapters={Channel.EMAIL: down}) is False
    assert (row.ops_emailed_at, row.receipt_sent_at) == (None, None)
    up = FakeAdapter()
    assert await applications.send_emails(db_session, row.id, adapters={Channel.EMAIL: up}) is True
    assert len(up.sent) == 2


async def test_unconfigured_email_returns_false_instead_of_raising(db_session: AsyncSession) -> None:
    row = await make_application(db_session)
    assert await applications.send_emails(db_session, row.id, adapters={}) is False
