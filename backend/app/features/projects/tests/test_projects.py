"""POST /projects (with the contractor invite), GET /projects (paginated) and GET /projects/{id}."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.core.errors import AppError
from app.features.projects import service
from app.features.projects.models import Project
from app.features.projects.tests.factories import (
    FENCE,
    INSIDE,
    audit_entries,
    bearer,
    make_project,
    make_user,
    project_data,
    random_phone,
)

BODY: dict[str, Any] = {
    "title": "4-bedroom duplex",
    "address": "12 Chime Avenue, Enugu",
    "currency": "NGN",
    "budget_minor": 45_000_000_00,
}


async def _user_by_phone(session: AsyncSession, phone: str) -> User | None:
    return await session.scalar(select(User).where(User.phone == phone))


# --- create -------------------------------------------------------------------------------------


async def test_client_creates_a_draft_project(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    response = await client.post("/api/v1/projects", json=BODY, headers=bearer(owner))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["client_id"] == str(owner.id)
    assert body["contractor_id"] is None
    assert body["supervisor_id"] is None
    assert body["budget_minor"] == 45_000_000_00
    assert body["currency"] == "NGN"


async def test_create_writes_an_audit_entry(db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    project = await service.create_project(db_session, owner, project_data())
    [entry] = await audit_entries(db_session, project.id)
    assert entry.action == "project.created"
    assert entry.object_type == "project"
    assert entry.actor_id == owner.id
    assert entry.before is None
    assert entry.after is not None and entry.after["status"] == "draft"


async def test_inviting_a_new_number_creates_a_contractor(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session, "client")
    local = f"0803{random_phone()[-7:]}"  # Nigerian local format, stored as +234...
    response = await client.post(
        "/api/v1/projects", json=BODY | {"contractor_phone": local}, headers=bearer(owner)
    )
    assert response.status_code == 201, response.text
    contractor = await _user_by_phone(db_session, "+234" + local[1:])
    assert contractor is not None
    assert contractor.role == "contractor"
    assert contractor.status == "active"
    assert response.json()["contractor_id"] == str(contractor.id)


async def test_inviting_an_existing_contractor_reuses_the_account(db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    contractor = await make_user(db_session, "contractor")
    assert contractor.phone is not None
    project = await service.create_project(db_session, owner, project_data(contractor_phone=contractor.phone))
    assert project.contractor_id == contractor.id
    count = await db_session.scalar(
        select(func.count()).select_from(User).where(User.phone == contractor.phone)
    )
    assert count == 1


@pytest.mark.parametrize("role", ["client", "supervisor", "supplier", "ops"])
async def test_inviting_a_non_contractor_is_409_and_keeps_their_role(
    db_session: AsyncSession, role: str
) -> None:
    owner = await make_user(db_session, "client")
    other = await make_user(db_session, role)
    with pytest.raises(AppError) as caught:
        await service.create_project(db_session, owner, project_data(contractor_phone=other.phone))
    assert (caught.value.code, caught.value.status_code) == ("role_conflict", 409)
    await db_session.refresh(other)
    assert other.role == role


async def test_inviting_yourself_is_409(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    response = await client.post(
        "/api/v1/projects", json=BODY | {"contractor_phone": owner.phone}, headers=bearer(owner)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "role_conflict"


async def test_inviting_a_suspended_contractor_is_409(db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    contractor = await make_user(db_session, "contractor", status="suspended")
    with pytest.raises(AppError) as caught:
        await service.create_project(db_session, owner, project_data(contractor_phone=contractor.phone))
    assert caught.value.code == "contractor_suspended"


@pytest.mark.parametrize(
    ("phone", "code"),
    [
        ("12345678", "invalid_phone"),
        ("447400123456", "phone_needs_country_code"),
        ("builder@example.com", "invalid_phone"),
    ],
)
async def test_bad_contractor_phone_is_422(
    client: AsyncClient, db_session: AsyncSession, phone: str, code: str
) -> None:
    owner = await make_user(db_session, "client")
    response = await client.post(
        "/api/v1/projects", json=BODY | {"contractor_phone": phone}, headers=bearer(owner)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert (
        await db_session.scalar(
            select(func.count()).select_from(Project).where(Project.client_id == owner.id)
        )
        == 0
    )


async def test_foreign_contractor_number_is_accepted(db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    project = await service.create_project(
        db_session, owner, project_data(contractor_phone="+44 7400 123456")
    )
    contractor = await _user_by_phone(db_session, "+447400123456")
    assert contractor is not None and project.contractor_id == contractor.id


@pytest.mark.parametrize(
    "change",
    [
        {"budget_minor": 100.0},  # money is never a float, even a whole one
        {"budget_minor": 12.5},
        {"budget_minor": "100"},
        {"budget_minor": 0},
        {"budget_minor": -1},
        {"currency": "ngn"},
        {"currency": "NAIRA"},
        {"title": "   "},
        {"address": ""},
        {"title": "x" * 201},
    ],
)
async def test_invalid_body_is_422(
    client: AsyncClient, db_session: AsyncSession, change: dict[str, Any]
) -> None:
    owner = await make_user(db_session, "client")
    response = await client.post("/api/v1/projects", json=BODY | change, headers=bearer(owner))
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


async def test_service_refuses_non_clients(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    with pytest.raises(AppError) as caught:
        await service.create_project(db_session, ops, project_data())
    assert (caught.value.code, caught.value.status_code) == ("forbidden_role", 403)


async def test_same_idempotency_key_creates_one_project(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session, "client")
    headers = bearer(owner) | {"Idempotency-Key": "create-project-1"}
    first = await client.post("/api/v1/projects", json=BODY, headers=headers)
    second = await client.post("/api/v1/projects", json=BODY, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    count = await db_session.scalar(
        select(func.count()).select_from(Project).where(Project.client_id == owner.id)
    )
    assert count == 1


async def test_without_idempotency_key_each_post_creates_a_project(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session, "client")
    for _ in range(2):
        assert (await client.post("/api/v1/projects", json=BODY, headers=bearer(owner))).status_code == 201
    count = await db_session.scalar(
        select(func.count()).select_from(Project).where(Project.client_id == owner.id)
    )
    assert count == 2


# --- view and list --------------------------------------------------------------------------------


async def test_detail_includes_the_site_once_set(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    url = f"/api/v1/projects/{project.id}"

    before = await client.get(url, headers=bearer(owner))
    assert before.status_code == 200
    assert before.json()["site"] is None

    put = await client.put(f"{url}/site", json={"location": INSIDE, "geofence": FENCE}, headers=bearer(owner))
    assert put.status_code == 200, put.text

    after = (await client.get(url, headers=bearer(owner))).json()
    assert after["site"]["location"] == INSIDE
    assert after["site"]["geofence"]["type"] == "Polygon"
    assert after["site"]["geofence"]["coordinates"] == FENCE["coordinates"]


async def test_list_pages_newest_first_with_a_cursor(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    projects = [await make_project(db_session, client=owner) for _ in range(5)]
    expected = [str(p.id) for p in sorted(projects, key=lambda p: (p.created_at, p.id), reverse=True)]

    seen: list[str] = []
    cursor: str | None = None
    for _ in range(3):
        params: dict[str, Any] = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        page = (await client.get("/api/v1/projects", params=params, headers=bearer(owner))).json()
        seen += [item["id"] for item in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert seen == expected
    assert cursor is None


async def test_ops_lists_every_project(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    mine = await make_project(db_session)
    page, _ = await service.list_projects(db_session, ops, limit=200)
    assert mine.id in {p.id for p in page}


@pytest.mark.parametrize("params", [{"cursor": "not-a-cursor"}, {"limit": 0}, {"limit": 201}])
async def test_bad_list_parameters_are_422(
    client: AsyncClient, db_session: AsyncSession, params: dict[str, Any]
) -> None:
    owner = await make_user(db_session, "client")
    response = await client.get("/api/v1/projects", params=params, headers=bearer(owner))
    assert response.status_code == 422


async def test_budget_is_stored_as_bigint(db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    big = 9_000_000_000_000  # above 2**31: needs BIGINT
    project = await service.create_project(db_session, owner, project_data(budget_minor=big))
    stored = await db_session.scalar(select(Project.budget_minor).where(Project.id == project.id))
    assert stored == big and isinstance(stored, int)
