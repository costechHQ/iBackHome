"""Ops reads for the console: one application in full, the supervisor list with load and fit for a project,
and a project's spot checks. Needs Postgres (backend/conftest.py)."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.projects import service as projects
from app.features.projects.models import Project
from app.features.supervision import rotation, service
from app.features.supervision.schemas import DeclaredRelation
from app.features.supervision.tests.factories import (
    CONTRACTOR_PHONE,
    application,
    bearer,
    make_user,
    make_vetted,
)

# GET /supervisors/{id}/application


async def test_ops_read_an_application_in_full(
    client: AsyncClient, db_session: AsyncSession, ops: User, applicant: User
) -> None:
    relative = DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="cousin")
    await service.submit_application(db_session, applicant.id, application(relative))

    response = await client.get(f"/api/v1/supervisors/{applicant.id}/application", headers=bearer(ops))

    assert response.status_code == 200
    body = response.json()
    assert body["vetting_status"] == "pending"
    assert body["phone"] == applicant.phone
    assert body["account_status"] == "active"
    assert body["guarantor_1"] == "Ngozi Eze, +2348031234567"
    assert body["guarantor_2"] == "Emeka Obi, +2348039876543"
    assert body["related_contractors"] == [{"contractor_phone": CONTRACTOR_PHONE, "relationship": "cousin"}]
    assert body["submitted_at"]


async def test_only_ops_read_applications(
    client: AsyncClient, db_session: AsyncSession, applicant: User
) -> None:
    for role in ("supervisor", "client", "contractor"):
        someone = applicant if role == "supervisor" else await make_user(db_session, role)
        response = await client.get(
            f"/api/v1/supervisors/{applicant.id}/application", headers=bearer(someone)
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden_role"


async def test_an_unknown_application_is_404(client: AsyncClient, ops: User) -> None:
    response = await client.get(f"/api/v1/supervisors/{uuid.uuid4()}/application", headers=bearer(ops))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "supervisor_profile_not_found"


# GET /supervisors


async def test_the_list_is_approved_supervisors_by_default_with_their_load(
    client: AsyncClient, db_session: AsyncSession, ops: User, applicant: User, vetted: User, project: Project
) -> None:
    await projects.set_supervisor(db_session, project.id, vetted.id, ops.id)

    response = await client.get("/api/v1/supervisors", headers=bearer(ops))

    assert response.status_code == 200
    rows = {row["user_id"]: row for row in response.json()}
    assert str(applicant.id) not in rows
    assert rows[str(vetted.id)]["active_projects"] == 1
    assert rows[str(vetted.id)]["assigned_here"] is None
    pending = await client.get("/api/v1/supervisors?vetting_status=pending", headers=bearer(ops))
    assert str(applicant.id) in {row["user_id"] for row in pending.json()}


async def test_with_a_project_it_says_who_is_assigned_and_who_is_related(
    client: AsyncClient, db_session: AsyncSession, ops: User, vetted: User, project: Project
) -> None:
    relative = await make_vetted(
        db_session, ops, DeclaredRelation(contractor_phone=CONTRACTOR_PHONE, relationship="brother")
    )
    await projects.set_supervisor(db_session, project.id, vetted.id, ops.id)

    response = await client.get(f"/api/v1/supervisors?project_id={project.id}", headers=bearer(ops))

    rows = {row["user_id"]: row for row in response.json()}
    assert (rows[str(vetted.id)]["assigned_here"], rows[str(vetted.id)]["related_to_contractor"]) == (
        True,
        False,
    )
    assert rows[str(relative.id)]["related_to_contractor"] is True
    assert rows[str(relative.id)]["related_contractors"] == 1


async def test_a_completed_project_doesnt_count_as_load(
    db_session: AsyncSession, ops: User, vetted: User, project: Project
) -> None:
    await projects.set_supervisor(db_session, project.id, vetted.id, ops.id)
    project.status = "completed"
    await db_session.flush()

    assert (await projects.supervisor_loads(db_session)).get(vetted.id, 0) == 0


async def test_the_list_is_ops_only_and_checks_the_project(
    client: AsyncClient, db_session: AsyncSession, ops: User, vetted: User
) -> None:
    assert (await client.get("/api/v1/supervisors", headers=bearer(vetted))).status_code == 403
    missing = await client.get(f"/api/v1/supervisors?project_id={uuid.uuid4()}", headers=bearer(ops))
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "project_not_found"


# GET /projects/{id}/spot-checks


async def test_ops_list_a_projects_spot_checks_soonest_first(
    client: AsyncClient, db_session: AsyncSession, ops: User, project: Project
) -> None:
    visitor = await make_vetted(db_session, ops)
    later = datetime.now(UTC) + timedelta(days=3)
    sooner = datetime.now(UTC) + timedelta(days=1)
    await rotation.schedule_project_spot_check(db_session, project.id, visitor.id, later, ops.id)
    await rotation.schedule_project_spot_check(db_session, project.id, visitor.id, sooner, ops.id)

    response = await client.get(f"/api/v1/projects/{project.id}/spot-checks", headers=bearer(ops))

    assert response.status_code == 200
    times = [row["scheduled_for"] for row in response.json()]
    assert len(times) == 2 and times == sorted(times)


async def test_nobody_else_sees_spot_checks(
    client: AsyncClient, db_session: AsyncSession, ops: User, project: Project
) -> None:
    contractor = await make_user(db_session, "contractor")
    response = await client.get(f"/api/v1/projects/{project.id}/spot-checks", headers=bearer(contractor))
    assert response.status_code == 403
    unknown = await client.get(f"/api/v1/projects/{uuid.uuid4()}/spot-checks", headers=bearer(ops))
    assert unknown.status_code == 404
