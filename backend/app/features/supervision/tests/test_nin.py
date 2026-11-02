"""A supervisor's NIN: encrypted while pending, shown only to ops (audited), wiped when they decide.

The thing these tests protect: the full number is never in a response to the applicant, the audit log,
an error message or a log line, and after the decision only its last 4 digits remain anywhere.
"""

import json
import logging
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.audit.service import snapshot
from app.core.config import get_settings
from app.core.errors import AppError
from app.features.supervision import nin as nin_store
from app.features.supervision import service
from app.features.supervision.models import SupervisorProfile
from app.features.supervision.schemas import SupervisorApplication
from app.features.supervision.tests.factories import ALL_CHECKS, application, approval, bearer, make_user

NIN = "12345678901"
KEY = "k" * 40
APPLICATION: dict[str, Any] = {
    "registration_body": "COREN",
    "registration_no": "R.98765",
    "guarantor_1": "Ngozi Eze, +2348031234567",
    "guarantor_2": "Emeka Obi, +2348039876543",
}


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "nin_encryption_key", KEY)


def put(client: AsyncClient, who: Any, **extra: Any) -> Any:
    return client.put("/api/v1/supervisors/me/profile", json={**APPLICATION, **extra}, headers=bearer(who))


async def everything_stored(session: AsyncSession) -> str:
    """Every audit entry and the profile row, as text: what a leak would be found in."""
    entries = await session.scalars(select(AuditEntry))
    profiles = await session.execute(text("select * from supervisor_profiles"))
    return json.dumps([{"b": e.before, "a": e.after} for e in entries], default=str) + str(
        profiles.fetchall()
    )


# --- the encryption itself ---------------------------------------------------------------------


def test_a_nin_round_trips_and_is_not_readable_in_the_token() -> None:
    token = nin_store.encrypt(NIN)
    assert NIN not in token
    assert nin_store.decrypt(token) == NIN


def test_two_encryptions_of_the_same_nin_differ() -> None:
    assert nin_store.encrypt(NIN) != nin_store.encrypt(NIN)


def test_a_changed_key_means_the_nin_is_gone_not_a_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    token = nin_store.encrypt(NIN)
    monkeypatch.setattr(get_settings(), "nin_encryption_key", "z" * 40)
    assert nin_store.decrypt(token) is None


@pytest.mark.parametrize("key", ["", "short", "x" * 31])
def test_without_a_proper_key_nothing_is_encrypted(monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    monkeypatch.setattr(get_settings(), "nin_encryption_key", key)
    with pytest.raises(AppError) as err:
        nin_store.encrypt(NIN)
    assert (err.value.code, err.value.status_code) == ("nin_not_configured", 503)


@pytest.mark.parametrize("value", [NIN, "00000000000", "99999999999"])
def test_eleven_digits_is_a_nin(value: str) -> None:
    assert nin_store.is_nin(value)


@pytest.mark.parametrize(
    "value", ["", "1234567890", "123456789012", "1234567890a", "1234 567 8901", "١٢٣٤٥٦٧٨٩٠١"]
)
def test_anything_else_is_not(value: str) -> None:
    assert not nin_store.is_nin(value)


# --- submitting --------------------------------------------------------------------------------


async def test_a_nin_is_stored_encrypted_with_its_last_four_and_never_returned(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    response = await put(client, supervisor, nin=NIN)
    assert response.status_code == 200, response.text
    assert response.json()["nin_last4"] == "8901"
    assert NIN not in response.text
    profile = await db_session.scalar(
        select(SupervisorProfile).where(SupervisorProfile.user_id == supervisor.id)
    )
    assert profile is not None
    assert profile.nin_last4 == "8901"
    assert profile.nin_encrypted and NIN not in profile.nin_encrypted
    assert nin_store.decrypt(profile.nin_encrypted) == NIN
    assert NIN not in (await client.get("/api/v1/supervisors/me/profile", headers=bearer(supervisor))).text


async def test_the_full_nin_never_reaches_the_audit_log(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    await put(client, supervisor, nin=NIN)
    profile = await db_session.scalar(
        select(SupervisorProfile).where(SupervisorProfile.user_id == supervisor.id)
    )
    assert profile is not None and profile.nin_encrypted
    logged = json.dumps(
        [{"b": e.before, "a": e.after} for e in await db_session.scalars(select(AuditEntry))], default=str
    )
    assert NIN not in logged
    assert profile.nin_encrypted not in logged  # not even the ciphertext: a later wipe could never reach it
    assert "nin_encrypted" not in logged
    assert "nin_last4" in logged  # the last four are fine to record


def test_snapshots_leave_out_any_column_marked_not_for_audit() -> None:
    profile = SupervisorProfile(nin_encrypted="secret-token", nin_last4="8901", registration_body="COREN")
    snap = snapshot(profile)
    assert "nin_encrypted" not in snap
    assert snap["nin_last4"] == "8901"


@pytest.mark.parametrize("bad", ["1234567890", "123456789012", "abcdefghijk", "1234 567 8901", ""])
async def test_a_bad_nin_is_422_and_the_message_never_echoes_it(
    client: AsyncClient, db_session: AsyncSession, bad: str
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    response = await put(client, supervisor, nin=bad)
    assert response.status_code == 422
    assert "11 digits" in response.json()["error"]["message"]
    if bad:
        assert bad not in response.text


async def test_without_a_server_key_a_nin_is_refused_and_nothing_is_saved(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "nin_encryption_key", "")
    supervisor = await make_user(db_session, "supervisor")
    response = await put(client, supervisor, nin=NIN)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "nin_not_configured"
    assert NIN not in response.text
    assert (
        await db_session.scalar(select(SupervisorProfile).where(SupervisorProfile.user_id == supervisor.id))
        is None
    )


async def test_an_application_without_a_nin_still_works_and_needs_no_key(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "nin_encryption_key", "")
    supervisor = await make_user(db_session, "supervisor")
    response = await put(client, supervisor)
    assert response.status_code == 200
    assert response.json()["nin_last4"] is None


async def test_resubmitting_without_a_nin_keeps_the_one_already_given(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    await put(client, supervisor, nin=NIN)
    response = await put(client, supervisor, registration_no="R.11111")
    assert response.json()["nin_last4"] == "8901"
    profile = await db_session.scalar(
        select(SupervisorProfile).where(SupervisorProfile.user_id == supervisor.id)
    )
    assert profile is not None and profile.nin_encrypted is not None


async def test_a_new_nin_replaces_the_old(client: AsyncClient, db_session: AsyncSession) -> None:
    supervisor = await make_user(db_session, "supervisor")
    await put(client, supervisor, nin=NIN)
    response = await put(client, supervisor, nin="98765432100")
    assert response.json()["nin_last4"] == "2100"


def test_the_application_never_prints_the_nin() -> None:
    parsed = SupervisorApplication.model_validate({**APPLICATION, "nin": NIN})
    assert NIN not in repr(parsed)
    assert NIN not in str(parsed)
    assert NIN not in parsed.model_dump_json()


async def test_nothing_in_the_logs_holds_the_nin(
    client: AsyncClient, db_session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    supervisor = await make_user(db_session, "supervisor")
    await put(client, supervisor, nin=NIN)
    await put(client, supervisor, nin="short")  # a rejected one too
    assert NIN not in caplog.text
    assert "short" not in caplog.text.replace("shortly", "")


# --- ops -------------------------------------------------------------------------------------


async def test_ops_see_the_full_nin_while_it_is_pending_and_the_view_is_audited(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    ops = await make_user(db_session, "ops")
    await put(client, supervisor, nin=NIN)
    response = await client.get(f"/api/v1/supervisors/{supervisor.id}/application", headers=bearer(ops))
    assert response.status_code == 200, response.text
    assert response.json()["nin"] == NIN
    assert response.json()["nin_last4"] == "8901"
    viewed = list(
        await db_session.scalars(select(AuditEntry).where(AuditEntry.action == "supervisor.nin_viewed"))
    )
    assert len(viewed) == 1
    assert viewed[0].actor_id == ops.id
    assert NIN not in json.dumps([viewed[0].before, viewed[0].after], default=str)


async def test_every_view_by_ops_is_its_own_audit_entry(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    ops = await make_user(db_session, "ops")
    await put(client, supervisor, nin=NIN)
    for _ in range(3):
        await client.get(f"/api/v1/supervisors/{supervisor.id}/application", headers=bearer(ops))
    viewed = list(
        await db_session.scalars(select(AuditEntry).where(AuditEntry.action == "supervisor.nin_viewed"))
    )
    assert len(viewed) == 3


async def test_an_application_with_no_nin_shows_none_and_audits_nothing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    ops = await make_user(db_session, "ops")
    await put(client, supervisor)
    body = (await client.get(f"/api/v1/supervisors/{supervisor.id}/application", headers=bearer(ops))).json()
    assert body["nin"] is None
    assert body["nin_last4"] is None
    viewed = list(
        await db_session.scalars(select(AuditEntry).where(AuditEntry.action == "supervisor.nin_viewed"))
    )
    assert viewed == []


@pytest.mark.parametrize("role", ["client", "contractor", "supervisor", "supplier"])
async def test_nobody_but_ops_can_read_an_application(
    client: AsyncClient, db_session: AsyncSession, role: str
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    await put(client, supervisor, nin=NIN)
    other = await make_user(db_session, role)
    response = await client.get(f"/api/v1/supervisors/{supervisor.id}/application", headers=bearer(other))
    assert response.status_code == 403
    assert NIN not in response.text


async def test_a_changed_key_shows_ops_no_nin_rather_than_garbage(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    ops = await make_user(db_session, "ops")
    await put(client, supervisor, nin=NIN)
    monkeypatch.setattr(get_settings(), "nin_encryption_key", "z" * 40)
    body = (await client.get(f"/api/v1/supervisors/{supervisor.id}/application", headers=bearer(ops))).json()
    assert body["nin"] is None
    assert body["nin_last4"] == "8901"


# --- the decision wipes it -----------------------------------------------------------------------


@pytest.mark.parametrize("decision", ["approved", "rejected"])
async def test_the_decision_wipes_the_full_nin_and_keeps_the_last_four(
    client: AsyncClient, db_session: AsyncSession, decision: str
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    ops = await make_user(db_session, "ops")
    await put(client, supervisor, nin=NIN)
    body = {
        "decision": decision,
        **ALL_CHECKS,
        **({"reason": "Details did not match."} if decision == "rejected" else {}),
    }
    response = await client.post(
        f"/api/v1/supervisors/{supervisor.id}/vetting", json=body, headers=bearer(ops)
    )
    assert response.status_code == 200, response.text
    assert response.json()["nin_last4"] == "8901"

    profile = await db_session.scalar(
        select(SupervisorProfile).where(SupervisorProfile.user_id == supervisor.id)
    )
    assert profile is not None
    await db_session.refresh(profile)
    assert profile.nin_encrypted is None
    assert profile.nin_last4 == "8901"
    assert NIN not in await everything_stored(db_session)

    after = (await client.get(f"/api/v1/supervisors/{supervisor.id}/application", headers=bearer(ops))).json()
    assert after["nin"] is None
    assert after["nin_last4"] == "8901"


async def test_a_rejected_applicant_gives_the_nin_again_when_they_re_apply(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    ops = await make_user(db_session, "ops")
    await put(client, supervisor, nin=NIN)
    await client.post(
        f"/api/v1/supervisors/{supervisor.id}/vetting",
        json={"decision": "rejected", "reason": "NIN did not match."},
        headers=bearer(ops),
    )
    await put(client, supervisor, nin="11122233344")
    body = (await client.get(f"/api/v1/supervisors/{supervisor.id}/application", headers=bearer(ops))).json()
    assert body["vetting_status"] == "pending"
    assert body["nin"] == "11122233344"


async def test_the_service_wipes_on_approval_too(db_session: AsyncSession) -> None:
    supervisor = await make_user(db_session, "supervisor")
    ops = await make_user(db_session, "ops")
    await service.submit_application(db_session, supervisor.id, application())
    await service.submit_application(
        db_session, supervisor.id, SupervisorApplication.model_validate({**APPLICATION, "nin": NIN})
    )
    profile = await service.vet(db_session, supervisor.id, approval(), ops.id)
    assert profile.nin_encrypted is None
    assert profile.nin_last4 == "8901"
