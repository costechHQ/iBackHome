"""GET /projects/{id} names the contractor and supervisor (MX-26), with a phone only for active accounts."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.projects.tests.factories import bearer, make_project, make_user


async def _named(session: AsyncSession, role: str, name: str) -> User:
    user = await make_user(session, role)
    user.full_name = name
    await session.flush()
    return user


async def _setup(session: AsyncSession):  # type: ignore[no-untyped-def]
    client_user = await _named(session, "client", "Chioma Okafor")
    contractor = await _named(session, "contractor", "Chukwuemeka Nwosu")
    supervisor = await _named(session, "supervisor", "Ifeoma Eze")
    project = await make_project(session, client=client_user, contractor=contractor, supervisor=supervisor)
    return project, client_user, contractor, supervisor


async def test_every_member_sees_both_names_and_phones(client: AsyncClient, db_session: AsyncSession) -> None:
    project, owner, contractor, supervisor = await _setup(db_session)
    ops = await make_user(db_session, "ops")
    for viewer in (owner, contractor, supervisor, ops):
        response = await client.get(f"/api/v1/projects/{project.id}", headers=bearer(viewer))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["contractor"] == {
            "id": str(contractor.id),
            "full_name": "Chukwuemeka Nwosu",
            "phone": contractor.phone,
        }
        assert body["supervisor"] == {
            "id": str(supervisor.id),
            "full_name": "Ifeoma Eze",
            "phone": supervisor.phone,
        }


async def test_a_party_has_only_id_name_and_phone(client: AsyncClient, db_session: AsyncSession) -> None:
    project, owner, _, _ = await _setup(db_session)
    body = (await client.get(f"/api/v1/projects/{project.id}", headers=bearer(owner))).json()
    assert set(body["contractor"]) == {"id", "full_name", "phone"}
    assert set(body["supervisor"]) == {"id", "full_name", "phone"}


async def test_no_contractor_or_supervisor_is_null(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    body = (await client.get(f"/api/v1/projects/{project.id}", headers=bearer(owner))).json()
    assert body["contractor"] is None
    assert body["supervisor"] is None
    assert body["contractor_id"] is None


async def test_a_suspended_account_keeps_its_name_but_loses_its_phone(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    project, owner, contractor, supervisor = await _setup(db_session)
    supervisor.status = "suspended"
    await db_session.flush()
    body = (await client.get(f"/api/v1/projects/{project.id}", headers=bearer(owner))).json()
    assert body["supervisor"]["full_name"] == "Ifeoma Eze"
    assert body["supervisor"]["phone"] is None
    assert body["contractor"]["phone"] == contractor.phone  # the other party is unaffected


async def test_an_email_only_account_has_no_phone(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    supervisor = User(
        email="site.lead@example.com", role="supervisor", status="active", full_name="Site Lead"
    )
    db_session.add(supervisor)
    await db_session.flush()
    project = await make_project(db_session, client=owner, supervisor=supervisor)
    body = (await client.get(f"/api/v1/projects/{project.id}", headers=bearer(owner))).json()
    assert body["supervisor"] == {"id": str(supervisor.id), "full_name": "Site Lead", "phone": None}


async def test_an_unnamed_person_has_a_null_name(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    contractor = await make_user(db_session, "contractor")  # invited by phone, never filled in a name
    project = await make_project(db_session, client=owner, contractor=contractor)
    body = (await client.get(f"/api/v1/projects/{project.id}", headers=bearer(owner))).json()
    assert body["contractor"]["full_name"] is None
    assert body["contractor"]["phone"] == contractor.phone


async def test_a_non_member_gets_403_and_no_names_or_phones(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    project, _, contractor, _ = await _setup(db_session)
    stranger = await make_user(db_session, "client")
    response = await client.get(f"/api/v1/projects/{project.id}", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"
    assert contractor.phone not in response.text


async def test_the_project_list_does_not_carry_phones(client: AsyncClient, db_session: AsyncSession) -> None:
    _, owner, contractor, supervisor = await _setup(db_session)
    response = await client.get("/api/v1/projects", headers=bearer(owner))
    assert response.status_code == 200
    assert contractor.phone not in response.text
    assert supervisor.phone not in response.text
