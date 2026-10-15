"""HTTP endpoints for vetting and spot checks. Needs Postgres (backend/conftest.py)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.projects.models import Project
from app.features.supervision import rotation, service
from app.features.supervision.models import SpotCheck
from app.features.supervision.schemas import DeclaredRelation
from app.features.supervision.tests.factories import (
    ALL_CHECKS,
    CONTRACTOR_PHONE,
    bearer,
    make_user,
    make_vetted,
)

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


# Audit


async def audit_actions(client: AsyncClient, ops: User, object_id: object) -> list[str]:
    response = await client.get(f"/api/v1/ops/audit?object_id={object_id}", headers=bearer(ops))
    assert response.status_code == 200
    return [entry["action"] for entry in response.json()["items"]]


async def test_applying_and_vetting_are_audited(
    client: AsyncClient, db_session: AsyncSession, ops: User
) -> None:
    supervisor = await make_user(db_session, "supervisor")
    applied = await client.put("/api/v1/supervisors/me/profile", json=APPLICATION, headers=bearer(supervisor))
    profile_id = (await service.get_profile(db_session, supervisor.id)).id

    await client.post(f"/api/v1/supervisors/{supervisor.id}/vetting", json=APPROVE, headers=bearer(ops))

    assert applied.status_code == 200
    assert await audit_actions(client, ops, profile_id) == ["supervisor.approved", "supervisor.applied"]


# POST /projects/{id}/supervisor


async def test_ops_assigns_a_vetted_supervisor(
    client: AsyncClient, ops: User, vetted: User, project: Project
) -> None:
    response = await client.post(
        f"/api/v1/projects/{project.id}/supervisor",
        json={"supervisor_id": str(vetted.id)},
        headers=bearer(ops),
    )

    assert response.status_code == 200
    assert response.json() == {"project_id": str(project.id), "supervisor_id": str(vetted.id)}
    assert project.supervisor_id == vetted.id


async def test_unvetted_supervisor_cannot_be_assigned(
    client: AsyncClient, ops: User, applicant: User, project: Project
) -> None:
    response = await client.post(
        f"/api/v1/projects/{project.id}/supervisor",
        json={"supervisor_id": str(applicant.id)},
        headers=bearer(ops),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "supervisor_not_vetted"


async def test_related_supervisor_cannot_be_assigned(
    client: AsyncClient, db_session: AsyncSession, ops: User, project: Project
) -> None:
    cousin = await make_vetted(
        db_session, ops, DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="cousin")
    )

    response = await client.post(
        f"/api/v1/projects/{project.id}/supervisor",
        json={"supervisor_id": str(cousin.id)},
        headers=bearer(ops),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "supervisor_related_to_contractor"


async def test_only_ops_can_assign(
    client: AsyncClient, db_session: AsyncSession, vetted: User, project: Project
) -> None:
    client_user = await make_user(db_session, "client")

    response = await client.post(
        f"/api/v1/projects/{project.id}/supervisor",
        json={"supervisor_id": str(vetted.id)},
        headers=bearer(client_user),
    )

    assert response.status_code == 403


async def test_assigning_to_unknown_project_is_404(client: AsyncClient, ops: User, vetted: User) -> None:
    response = await client.post(
        f"/api/v1/projects/{uuid.uuid4()}/supervisor",
        json={"supervisor_id": str(vetted.id)},
        headers=bearer(ops),
    )

    assert response.status_code == 404


# POST /projects/{id}/spot-checks


def tomorrow() -> str:
    return (datetime.now(UTC) + timedelta(days=1)).isoformat()


async def test_ops_schedules_a_spot_check(
    client: AsyncClient, ops: User, vetted: User, project: Project
) -> None:
    response = await client.post(
        f"/api/v1/projects/{project.id}/spot-checks",
        json={"supervisor_id": str(vetted.id), "scheduled_for": tomorrow()},
        headers=bearer(ops),
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["project_id"], body["supervisor_id"]) == (str(project.id), str(vetted.id))
    assert await audit_actions(client, ops, body["id"]) == ["spot_check.scheduled"]


async def test_spot_check_time_without_timezone_is_422(
    client: AsyncClient, ops: User, vetted: User, project: Project
) -> None:
    naive = (datetime.now(UTC) + timedelta(days=1)).replace(tzinfo=None).isoformat()

    response = await client.post(
        f"/api/v1/projects/{project.id}/spot-checks",
        json={"supervisor_id": str(vetted.id), "scheduled_for": naive},
        headers=bearer(ops),
    )

    assert response.status_code == 422


async def test_contractor_cannot_schedule_spot_checks(
    client: AsyncClient, db_session: AsyncSession, vetted: User, project: Project
) -> None:
    contractor = await make_user(db_session, "contractor")

    response = await client.post(
        f"/api/v1/projects/{project.id}/spot-checks",
        json={"supervisor_id": str(vetted.id), "scheduled_for": tomorrow()},
        headers=bearer(contractor),
    )

    assert response.status_code == 403


# GET /supervisors/me/spot-checks and POST /spot-checks/{id}/complete


async def scheduled(session: AsyncSession, project: Project, visitor: User, ops: User) -> SpotCheck:
    return await rotation.schedule_project_spot_check(
        session, project.id, visitor.id, datetime.now(UTC) + timedelta(days=1), ops.id
    )


async def test_supervisor_lists_and_completes_their_spot_check(
    client: AsyncClient, db_session: AsyncSession, vetted: User, ops: User, project: Project
) -> None:
    spot_check = await scheduled(db_session, project, vetted, ops)

    listed = await client.get("/api/v1/supervisors/me/spot-checks", headers=bearer(vetted))
    assert [s["id"] for s in listed.json()] == [str(spot_check.id)]

    done = await client.post(
        f"/api/v1/spot-checks/{spot_check.id}/complete",
        json={"findings": "Columns match the drawings."},
        headers=bearer(vetted),
    )
    assert done.status_code == 200
    assert done.json()["completed_at"] is not None
    assert await audit_actions(client, ops, spot_check.id) == ["spot_check.completed", "spot_check.scheduled"]


async def test_contractor_cannot_see_or_complete_spot_checks(
    client: AsyncClient, db_session: AsyncSession, vetted: User, ops: User, project: Project
) -> None:
    contractor = await make_user(db_session, "contractor")
    spot_check = await scheduled(db_session, project, vetted, ops)

    listed = await client.get("/api/v1/supervisors/me/spot-checks", headers=bearer(contractor))
    done = await client.post(
        f"/api/v1/spot-checks/{spot_check.id}/complete",
        json={"findings": "Trying to close it early."},
        headers=bearer(contractor),
    )

    assert (listed.status_code, done.status_code) == (403, 403)


async def test_completing_someone_elses_spot_check_is_404(
    client: AsyncClient, db_session: AsyncSession, vetted: User, ops: User, project: Project
) -> None:
    other = await make_user(db_session, "supervisor")
    spot_check = await scheduled(db_session, project, vetted, ops)

    response = await client.post(
        f"/api/v1/spot-checks/{spot_check.id}/complete",
        json={"findings": "This visit isn't mine."},
        headers=bearer(other),
    )

    assert response.status_code == 404
