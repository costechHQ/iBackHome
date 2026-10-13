"""HTTP endpoints for vetting and spot checks. Needs Postgres (backend/conftest.py)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.supervision import service
from app.features.supervision.tests.factories import ALL_CHECKS, bearer, make_user

APPLICATION: dict[str, Any] = {
    "registration_body": "COREN",
    "registration_no": "R.98765",
    "guarantor_1": "Ngozi Eze, +2348031234567",
    "guarantor_2": "Emeka Obi, +2348039876543",
    "related_contractors": [{"contractor_phone": "08012345678", "relationship": "cousin"}],
}
APPROVE = {"decision": "approved", **ALL_CHECKS}


# PUT/GET /supervisors/me/profile


async def test_supervisor_applies_and_sees_pending(client: AsyncClient, db_session: AsyncSession) -> None:
    supervisor = await make_user(db_session, "supervisor")

    response = await client.put(
        "/api/v1/supervisors/me/profile", json=APPLICATION, headers=bearer(supervisor)
    )

    assert response.status_code == 200
    assert response.json()["vetting_status"] == "pending"
    assert await service.is_related(db_session, supervisor.id, "+2348012345678")
    mine = await client.get("/api/v1/supervisors/me/profile", headers=bearer(supervisor))
    assert (mine.status_code, mine.json()["registration_no"]) == (200, "R.98765")


async def test_only_supervisors_can_apply(client: AsyncClient, db_session: AsyncSession) -> None:
    contractor = await make_user(db_session, "contractor")

    response = await client.put(
        "/api/v1/supervisors/me/profile", json=APPLICATION, headers=bearer(contractor)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"


async def test_applying_needs_sign_in(client: AsyncClient) -> None:
    response = await client.put("/api/v1/supervisors/me/profile", json=APPLICATION)

    assert response.status_code == 401


async def test_profile_before_applying_is_404(client: AsyncClient, db_session: AsyncSession) -> None:
    supervisor = await make_user(db_session, "supervisor")

    response = await client.get("/api/v1/supervisors/me/profile", headers=bearer(supervisor))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "supervisor_profile_not_found"


# POST /supervisors/{id}/vetting


async def test_ops_approves_a_supervisor(client: AsyncClient, ops: User, applicant: User) -> None:
    response = await client.post(
        f"/api/v1/supervisors/{applicant.id}/vetting", json=APPROVE, headers=bearer(ops)
    )

    assert response.status_code == 200
    assert response.json()["vetting_status"] == "approved"


async def test_approval_with_a_check_missing_is_422(client: AsyncClient, ops: User, applicant: User) -> None:
    body = APPROVE | {"nin_verified": False}

    response = await client.post(
        f"/api/v1/supervisors/{applicant.id}/vetting", json=body, headers=bearer(ops)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "vetting_checks_incomplete"


async def test_rejection_without_reason_is_422(client: AsyncClient, ops: User, applicant: User) -> None:
    response = await client.post(
        f"/api/v1/supervisors/{applicant.id}/vetting", json={"decision": "rejected"}, headers=bearer(ops)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_supervisor_cannot_vet_themselves(client: AsyncClient, applicant: User) -> None:
    response = await client.post(
        f"/api/v1/supervisors/{applicant.id}/vetting", json=APPROVE, headers=bearer(applicant)
    )

    assert response.status_code == 403


async def test_vetting_unknown_supervisor_is_404(client: AsyncClient, ops: User) -> None:
    response = await client.post(
        f"/api/v1/supervisors/{uuid.uuid4()}/vetting", json=APPROVE, headers=bearer(ops)
    )

    assert response.status_code == 404


async def test_repeated_vetting_with_same_key_replays(
    client: AsyncClient, ops: User, applicant: User
) -> None:
    headers = bearer(ops) | {"Idempotency-Key": "vet-once-123"}
    url = f"/api/v1/supervisors/{applicant.id}/vetting"

    first = await client.post(url, json=APPROVE, headers=headers)
    second = await client.post(url, json=APPROVE, headers=headers)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


# Spot checks


async def test_supervisor_lists_and_completes_their_spot_check(
    client: AsyncClient, db_session: AsyncSession, vetted: User, ops: User
) -> None:
    spot_check = await service.schedule_spot_check(
        db_session, uuid.uuid4(), vetted.id, datetime.now(UTC) + timedelta(days=1), ops.id
    )

    listed = await client.get("/api/v1/supervisors/me/spot-checks", headers=bearer(vetted))
    assert [s["id"] for s in listed.json()] == [str(spot_check.id)]

    done = await client.post(
        f"/api/v1/spot-checks/{spot_check.id}/complete",
        json={"findings": "Columns match the drawings."},
        headers=bearer(vetted),
    )
    assert done.status_code == 200
    assert done.json()["completed_at"] is not None


async def test_contractor_cannot_see_or_complete_spot_checks(
    client: AsyncClient, db_session: AsyncSession, vetted: User, ops: User
) -> None:
    contractor = await make_user(db_session, "contractor")
    spot_check = await service.schedule_spot_check(
        db_session, uuid.uuid4(), vetted.id, datetime.now(UTC) + timedelta(days=1), ops.id
    )

    listed = await client.get("/api/v1/supervisors/me/spot-checks", headers=bearer(contractor))
    done = await client.post(
        f"/api/v1/spot-checks/{spot_check.id}/complete",
        json={"findings": "Trying to close it early."},
        headers=bearer(contractor),
    )

    assert (listed.status_code, done.status_code) == (403, 403)


async def test_completing_someone_elses_spot_check_is_404(
    client: AsyncClient, db_session: AsyncSession, vetted: User, ops: User
) -> None:
    other = await make_user(db_session, "supervisor")
    spot_check = await service.schedule_spot_check(
        db_session, uuid.uuid4(), vetted.id, datetime.now(UTC) + timedelta(days=1), ops.id
    )

    response = await client.post(
        f"/api/v1/spot-checks/{spot_check.id}/complete",
        json={"findings": "This visit isn't mine."},
        headers=bearer(other),
    )

    assert response.status_code == 404
