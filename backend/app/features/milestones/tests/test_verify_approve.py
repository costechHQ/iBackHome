"""Day 3: POST /milestones/{id}/verify, POST /milestones/{id}/approve, GET /projects/{id}/milestones.

These run against a real project (projects.service) with real sign-in tokens. Abigail's
evidence check is replaced per test with the set of accepted photo IDs.
"""

import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.core.errors import AppError
from app.features.escrow import service as escrow
from app.features.escrow.tests.release_helpers import hold_money
from app.features.evidence import service as evidence_service
from app.features.milestones import evidence_check, service
from app.features.milestones.models import MilestoneStatus as S
from app.features.milestones.models import Verification
from app.features.milestones.schemas import VerifyIn
from app.features.milestones.tests.factories import (
    Site,
    active_project,
    audit_actions,
    bearer,
    make_user,
    set_project_status,
)
from app.features.milestones.transitions import ActorRole
from app.features.projects import service as projects_service

PHOTO_A, PHOTO_B, CONTRACTOR_PHOTO = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def accepted(monkeypatch: pytest.MonkeyPatch, *ids: uuid.UUID) -> None:
    """Pretend these photos are this milestone's accepted supervisor evidence."""

    async def fake(_: AsyncSession, __: uuid.UUID) -> set[uuid.UUID]:
        return set(ids)

    monkeypatch.setattr(evidence_check, "accepted_evidence_ids", fake)


def verified_body(*photos: uuid.UUID) -> dict[str, Any]:
    photos = photos or (PHOTO_A,)
    return {
        "decision": "verified",
        "checklist": [
            {"item": "Trench depth as drawn", "passed": True, "evidence_ids": [str(photos[0])]},
            {"item": "Rebar spacing", "passed": True, "evidence_ids": [str(p) for p in photos]},
        ],
        "notes": "All good",
    }


REJECTED = {"decision": "rejected", "notes": "Blockwork not plumb on the east wall"}


async def verification_count(session: AsyncSession, milestone_id: uuid.UUID) -> int:
    count = await session.scalar(
        select(func.count()).select_from(Verification).where(Verification.milestone_id == milestone_id)
    )
    return count or 0


@pytest.fixture
async def site(db_session: AsyncSession) -> Site:
    return await active_project(db_session)


def verify_url(site: Site) -> str:
    return f"/api/v1/milestones/{site.milestones[0].id}/verify"


def approve_url(site: Site) -> str:
    return f"/api/v1/milestones/{site.milestones[0].id}/approve"


# --- verify ------------------------------------------------------------------------------------


async def test_supervisor_verifies_with_accepted_photos(
    client: AsyncClient, db_session: AsyncSession, site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    accepted(monkeypatch, PHOTO_A, PHOTO_B)
    response = await client.post(
        verify_url(site), json=verified_body(PHOTO_A, PHOTO_B), headers=bearer(site.supervisor)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["milestone"]["status"] == "verified"
    assert body["milestone"]["verified_at"] is not None
    assert body["verification"]["decision"] == "verified"
    assert body["verification"]["supervisor_id"] == str(site.supervisor.id)
    assert body["verification"]["checklist"][1]["evidence_ids"] == [str(PHOTO_A), str(PHOTO_B)]

    milestone_id = site.milestones[0].id
    assert await verification_count(db_session, milestone_id) == 1
    assert await audit_actions(db_session, milestone_id) == ["milestone.verified"]
    verification_id = uuid.UUID(body["verification"]["id"])
    assert await audit_actions(db_session, verification_id) == ["verification.verified"]


async def test_supervisor_rejects_with_a_reason(
    client: AsyncClient, db_session: AsyncSession, site: Site
) -> None:
    site.milestones[0].claimed_at = site.milestones[0].created_at
    await db_session.flush()
    response = await client.post(verify_url(site), json=REJECTED, headers=bearer(site.supervisor))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["milestone"]["status"] == "funded"  # back to the contractor for rework
    assert body["milestone"]["claimed_at"] is None
    assert body["verification"]["decision"] == "rejected"
    assert body["verification"]["notes"] == REJECTED["notes"]
    assert await audit_actions(db_session, site.milestones[0].id) == ["milestone.funded"]


async def test_rejection_needs_no_evidence_check(
    client: AsyncClient, site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def must_not_run(*_: object) -> set[uuid.UUID]:
        raise AssertionError("evidence is not needed to reject")

    monkeypatch.setattr(evidence_check, "accepted_evidence_ids", must_not_run)
    response = await client.post(verify_url(site), json=REJECTED, headers=bearer(site.supervisor))
    assert response.status_code == 200


@pytest.mark.parametrize(
    "accepted_ids",
    [
        (),  # nothing accepted yet (still uploading or being checked)
        (PHOTO_A,),  # one of the two photos is not accepted (flagged, rejected or pending)
        (PHOTO_B, CONTRACTOR_PHOTO),  # contractor uploads are never in the accepted set
    ],
)
async def test_verify_refused_until_every_checklist_photo_is_accepted(
    client: AsyncClient,
    db_session: AsyncSession,
    site: Site,
    monkeypatch: pytest.MonkeyPatch,
    accepted_ids: tuple[uuid.UUID, ...],
) -> None:
    accepted(monkeypatch, *accepted_ids)
    response = await client.post(
        verify_url(site), json=verified_body(PHOTO_A, PHOTO_B), headers=bearer(site.supervisor)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "evidence_not_accepted"
    assert (await service.get_milestone(db_session, site.milestones[0].id)).status == S.CLAIMED
    assert await verification_count(db_session, site.milestones[0].id) == 0


async def test_only_the_assigned_supervisor_can_verify(
    client: AsyncClient, db_session: AsyncSession, site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    accepted(monkeypatch, PHOTO_A)
    other = await make_user(db_session, "supervisor")
    response = await client.post(verify_url(site), json=verified_body(), headers=bearer(other))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_assigned_supervisor"


@pytest.mark.parametrize("who", ["client", "contractor", "ops"])
async def test_other_roles_cannot_verify(client: AsyncClient, site: Site, who: str) -> None:
    user: User = getattr(site, who)
    response = await client.post(verify_url(site), json=REJECTED, headers=bearer(user))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"


async def test_verify_needs_sign_in(client: AsyncClient, site: Site) -> None:
    response = await client.post(verify_url(site), json=REJECTED)
    assert response.status_code == 401


@pytest.mark.parametrize("status", [S.FUNDED, S.VERIFIED, S.DISPUTED, S.RELEASED])
async def test_verify_refused_unless_claimed(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, status: S
) -> None:
    """Includes the offline case: the milestone was disputed while the supervisor had no signal."""
    accepted(monkeypatch, PHOTO_A)
    site = await active_project(db_session, first_status=status)
    response = await client.post(verify_url(site), json=verified_body(), headers=bearer(site.supervisor))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_transition"


async def test_verify_refused_on_a_paused_project(
    client: AsyncClient, db_session: AsyncSession, site: Site
) -> None:
    await set_project_status(db_session, site.project_id, "paused")
    response = await client.post(verify_url(site), json=REJECTED, headers=bearer(site.supervisor))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "project_not_active"


async def test_verify_unknown_milestone(client: AsyncClient, site: Site) -> None:
    response = await client.post(
        f"/api/v1/milestones/{uuid.uuid4()}/verify", json=REJECTED, headers=bearer(site.supervisor)
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "milestone_not_found"


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "verified", "checklist": []},
        {
            "decision": "verified",
            "checklist": [{"item": "Rebar", "passed": False, "evidence_ids": [str(PHOTO_A)]}],
        },
        {"decision": "verified", "checklist": [{"item": "Rebar", "passed": True, "evidence_ids": []}]},
        {"decision": "rejected"},
        {"decision": "rejected", "notes": "   "},
        {"decision": "maybe", "notes": "x"},
        {"decision": "verified", "checklist": [{"item": "", "passed": True, "evidence_ids": [str(PHOTO_A)]}]},
    ],
    ids=[
        "no-checklist",
        "item-failed",
        "item-no-photo",
        "reject-no-reason",
        "reject-blank",
        "bad-decision",
        "blank-item",
    ],
)
async def test_verify_input_is_checked(client: AsyncClient, site: Site, body: dict[str, Any]) -> None:
    response = await client.post(verify_url(site), json=body, headers=bearer(site.supervisor))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_verify_retry_with_same_key_is_saved_once(
    client: AsyncClient, db_session: AsyncSession, site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The offline sync queue resends with the same Idempotency-Key."""
    accepted(monkeypatch, PHOTO_A)
    headers = bearer(site.supervisor) | {"Idempotency-Key": str(uuid.uuid4())}
    first = await client.post(verify_url(site), json=verified_body(), headers=headers)
    retry = await client.post(verify_url(site), json=verified_body(), headers=headers)
    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    assert await verification_count(db_session, site.milestones[0].id) == 1


async def test_verify_asks_the_evidence_feature(
    client: AsyncClient, site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[uuid.UUID] = []

    async def accepted_for_milestone(_: AsyncSession, milestone_id: uuid.UUID) -> list[SimpleNamespace]:
        calls.append(milestone_id)
        return [SimpleNamespace(id=PHOTO_A)]

    monkeypatch.setattr(evidence_service, "accepted_for_milestone", accepted_for_milestone)
    response = await client.post(verify_url(site), json=verified_body(), headers=bearer(site.supervisor))
    assert response.status_code == 200, response.text
    assert calls == [site.milestones[0].id]


# --- approve -----------------------------------------------------------------------------------


@pytest.fixture
def release_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[uuid.UUID, uuid.UUID]]:
    calls: list[tuple[uuid.UUID, uuid.UUID]] = []
    original: Callable[..., Any] = escrow.request_release

    async def spy(session: AsyncSession, milestone_id: uuid.UUID, actor: User) -> escrow.ReleaseRequest:
        calls.append((milestone_id, actor.id))
        result: escrow.ReleaseRequest = await original(session, milestone_id, actor)
        return result

    monkeypatch.setattr(escrow, "request_release", spy)
    return calls


async def test_client_approves_and_release_is_requested(
    client: AsyncClient,
    db_session: AsyncSession,
    release_calls: list[tuple[uuid.UUID, uuid.UUID]],
) -> None:
    site = await active_project(db_session, first_status=S.VERIFIED)
    await hold_money(db_session, site.project_id, site.milestones[0])  # a release needs money in escrow
    response = await client.post(approve_url(site), headers=bearer(site.client))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"
    assert response.json()["approved_at"] is not None
    assert release_calls == [(site.milestones[0].id, site.client.id)]
    assert await audit_actions(db_session, site.milestones[0].id) == ["milestone.approved"]


async def test_nothing_is_saved_if_escrow_refuses(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = await active_project(db_session, first_status=S.VERIFIED)
    milestone_id = site.milestones[0].id

    async def refuse(*_: object) -> None:
        raise AppError("release_already_requested", "A release was already requested.", 409)

    monkeypatch.setattr(escrow, "request_release", refuse)
    with pytest.raises(AppError, match="already requested"):
        async with db_session.begin_nested():
            await service.approve(db_session, milestone_id, site.client)
    assert (await service.get_milestone(db_session, milestone_id, lock=True)).status == S.VERIFIED
    assert await audit_actions(db_session, milestone_id) == []


async def test_only_the_projects_client_can_approve(
    client: AsyncClient, db_session: AsyncSession, release_calls: list[tuple[uuid.UUID, uuid.UUID]]
) -> None:
    site = await active_project(db_session, first_status=S.VERIFIED)
    stranger = await make_user(db_session, "client")
    response = await client.post(approve_url(site), headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_client"
    assert release_calls == []


@pytest.mark.parametrize("who", ["contractor", "supervisor", "ops"])
async def test_other_roles_cannot_approve(client: AsyncClient, db_session: AsyncSession, who: str) -> None:
    site = await active_project(db_session, first_status=S.VERIFIED)
    response = await client.post(approve_url(site), headers=bearer(getattr(site, who)))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"


@pytest.mark.parametrize("status", [S.CLAIMED, S.FUNDED, S.APPROVED, S.DISPUTED, S.RELEASED])
async def test_approve_refused_unless_verified(
    client: AsyncClient,
    db_session: AsyncSession,
    release_calls: list[tuple[uuid.UUID, uuid.UUID]],
    status: S,
) -> None:
    site = await active_project(db_session, first_status=status)
    response = await client.post(approve_url(site), headers=bearer(site.client))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_transition"
    assert release_calls == []


async def test_approve_refused_on_a_paused_project(client: AsyncClient, db_session: AsyncSession) -> None:
    site = await active_project(db_session, first_status=S.VERIFIED)
    await set_project_status(db_session, site.project_id, "paused")
    response = await client.post(approve_url(site), headers=bearer(site.client))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "project_not_active"


async def test_approve_retry_with_same_key_releases_once(
    client: AsyncClient, db_session: AsyncSession, release_calls: list[tuple[uuid.UUID, uuid.UUID]]
) -> None:
    site = await active_project(db_session, first_status=S.VERIFIED)
    await hold_money(db_session, site.project_id, site.milestones[0])
    headers = bearer(site.client) | {"Idempotency-Key": str(uuid.uuid4())}
    first = await client.post(approve_url(site), headers=headers)
    retry = await client.post(approve_url(site), headers=headers)
    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    assert len(release_calls) == 1


# --- full flow and the project list ------------------------------------------------------------


async def test_claim_verify_approve_on_a_real_project(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    accepted(monkeypatch, PHOTO_A)
    site = await active_project(db_session, first_status=S.FUNDED)
    await hold_money(db_session, site.project_id, site.milestones[0])
    milestone_id = site.milestones[0].id

    claim = await client.post(f"/api/v1/milestones/{milestone_id}/claim", headers=bearer(site.contractor))
    assert claim.status_code == 200, claim.text
    verify = await client.post(verify_url(site), json=verified_body(), headers=bearer(site.supervisor))
    assert verify.status_code == 200, verify.text
    approve = await client.post(approve_url(site), headers=bearer(site.client))
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"
    assert await audit_actions(db_session, milestone_id) == [
        "milestone.claimed",
        "milestone.verified",
        "milestone.approved",
    ]


@pytest.mark.parametrize("who", ["client", "contractor", "supervisor", "ops"])
async def test_members_and_ops_list_the_milestones(
    client: AsyncClient, db_session: AsyncSession, site: Site, who: str
) -> None:
    await service.verify(
        db_session, site.milestones[0].id, site.supervisor, VerifyIn.model_validate(REJECTED)
    )
    response = await client.get(
        f"/api/v1/projects/{site.project_id}/milestones", headers=bearer(getattr(site, who))
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [(m["sequence"], m["name"], m["status"]) for m in body] == [
        (1, "Foundation", "funded"),
        (2, "Roofing", "pending"),
    ]
    assert body[0]["latest_verification"]["decision"] == "rejected"
    assert body[0]["latest_verification"]["notes"] == REJECTED["notes"]
    assert body[1]["latest_verification"] is None


async def test_latest_verification_is_the_newest(
    db_session: AsyncSession, site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    accepted(monkeypatch, PHOTO_A)
    milestone_id = site.milestones[0].id
    await service.verify(db_session, milestone_id, site.supervisor, VerifyIn.model_validate(REJECTED))
    await service.transition(db_session, milestone_id, S.CLAIMED, ActorRole.CONTRACTOR, site.contractor.id)
    await service.verify(db_session, milestone_id, site.supervisor, VerifyIn.model_validate(verified_body()))
    latest = await service.latest_verifications(db_session, [milestone_id])
    assert latest[milestone_id].decision == "verified"


async def test_outsiders_cannot_list_the_milestones(
    client: AsyncClient, db_session: AsyncSession, site: Site
) -> None:
    stranger = await make_user(db_session, "contractor")
    response = await client.get(f"/api/v1/projects/{site.project_id}/milestones", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"


async def test_list_unknown_project(client: AsyncClient, site: Site) -> None:
    response = await client.get(f"/api/v1/projects/{uuid.uuid4()}/milestones", headers=bearer(site.client))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "project_not_found"


# --- list_verifiers (James's rotation) ---------------------------------------------------------


async def test_list_verifiers_in_milestone_order(
    db_session: AsyncSession, site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    accepted(monkeypatch, PHOTO_A)
    first, second = site.milestones
    assert await service.list_verifiers(db_session, site.project_id) == []

    # Milestone 1: rejected once, then verified by the assigned supervisor.
    await service.verify(db_session, first.id, site.supervisor, VerifyIn.model_validate(REJECTED))
    await service.transition(db_session, first.id, S.CLAIMED, ActorRole.CONTRACTOR, site.contractor.id)
    await service.verify(db_session, first.id, site.supervisor, VerifyIn.model_validate(verified_body()))
    assert await service.list_verifiers(db_session, site.project_id) == [site.supervisor.id]

    # Milestone 2: verified by a new supervisor after a rotation.
    new_supervisor = await make_user(db_session, "supervisor")
    project = await projects_service.get_project(db_session, site.project_id)
    project.supervisor_id = new_supervisor.id
    second.status = S.CLAIMED
    await db_session.flush()
    await service.verify(db_session, second.id, new_supervisor, VerifyIn.model_validate(verified_body()))
    assert await service.list_verifiers(db_session, site.project_id) == [
        site.supervisor.id,
        new_supervisor.id,
    ]


async def test_list_verifiers_skips_milestones_sent_back_for_rework(
    db_session: AsyncSession, site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    accepted(monkeypatch, PHOTO_A)
    milestone_id = site.milestones[0].id
    await service.verify(db_session, milestone_id, site.supervisor, VerifyIn.model_validate(verified_body()))
    await service.transition(db_session, milestone_id, S.DISPUTED, ActorRole.CLIENT, site.client.id)
    assert await service.list_verifiers(db_session, site.project_id) == [site.supervisor.id]
    await service.transition(db_session, milestone_id, S.FUNDED, ActorRole.OPS, site.ops.id)  # rework
    assert await service.list_verifiers(db_session, site.project_id) == []
