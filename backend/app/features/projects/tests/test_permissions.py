"""Day 3 "done when": someone not on a project gets 403 on every project route.

Every route is called by every kind of user: the project's client, contractor and assigned
supervisor, ops, and outsiders of each role, plus no token at all.
"""

from dataclasses import dataclass

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.projects.models import Project
from app.features.projects.tests.factories import FENCE, INSIDE, bearer, make_project, make_user


@dataclass
class Cast:
    project: Project
    people: dict[str, User]


@pytest.fixture
async def cast(db_session: AsyncSession) -> Cast:
    contractor = await make_user(db_session, "contractor")
    supervisor = await make_user(db_session, "supervisor")
    client = await make_user(db_session, "client")
    project = await make_project(db_session, client=client, contractor=contractor, supervisor=supervisor)
    people = {
        "client": client,
        "contractor": contractor,
        "supervisor": supervisor,
        "ops": await make_user(db_session, "ops"),
        "other_client": await make_user(db_session, "client"),
        "other_contractor": await make_user(db_session, "contractor"),
        "other_supervisor": await make_user(db_session, "supervisor"),
        "supplier": await make_user(db_session, "supplier"),
    }
    return Cast(project=project, people=people)


def _headers(cast: Cast, who: str) -> dict[str, str]:
    return {} if who == "nobody" else bearer(cast.people[who])


VIEW = {
    "client": 200,
    "contractor": 200,
    "supervisor": 200,
    "ops": 200,
    "other_client": 403,
    "other_contractor": 403,
    "other_supervisor": 403,
    "supplier": 403,
    "nobody": 401,
}


@pytest.mark.parametrize(("who", "expected"), VIEW.items())
async def test_view_project(client: AsyncClient, cast: Cast, who: str, expected: int) -> None:
    response = await client.get(f"/api/v1/projects/{cast.project.id}", headers=_headers(cast, who))
    assert response.status_code == expected, response.text
    if expected == 403:
        assert response.json()["error"]["code"] == "not_project_member"


SET_SITE = {
    "client": (200, None),
    "ops": (200, None),
    "contractor": (403, "forbidden_role"),
    "supervisor": (403, "forbidden_role"),
    "other_client": (403, "not_project_member"),
    "other_contractor": (403, "forbidden_role"),
    "other_supervisor": (403, "forbidden_role"),
    "supplier": (403, "forbidden_role"),
    "nobody": (401, None),
}


@pytest.mark.parametrize(("who", "expected"), SET_SITE.items())
async def test_set_site(client: AsyncClient, cast: Cast, who: str, expected: tuple[int, str | None]) -> None:
    status, code = expected
    response = await client.put(
        f"/api/v1/projects/{cast.project.id}/site",
        json={"location": INSIDE, "geofence": FENCE},
        headers=_headers(cast, who),
    )
    assert response.status_code == status, response.text
    if code:
        assert response.json()["error"]["code"] == code


@pytest.mark.parametrize("who", list(VIEW))
async def test_list_shows_only_your_projects(client: AsyncClient, cast: Cast, who: str) -> None:
    response = await client.get("/api/v1/projects?limit=200", headers=_headers(cast, who))
    if who == "nobody":
        assert response.status_code == 401
        return
    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()["items"]}
    assert (str(cast.project.id) in ids) is (VIEW[who] == 200)


@pytest.mark.parametrize(
    ("who", "expected"),
    [
        ("client", 201),
        ("contractor", 403),
        ("supervisor", 403),
        ("supplier", 403),
        ("ops", 403),
        ("nobody", 401),
    ],
)
async def test_create_project(client: AsyncClient, cast: Cast, who: str, expected: int) -> None:
    body = {"title": "Bungalow", "address": "Enugu", "currency": "NGN", "budget_minor": 1_000_000}
    response = await client.post("/api/v1/projects", json=body, headers=_headers(cast, who))
    assert response.status_code == expected, response.text


async def test_unknown_project_is_404(client: AsyncClient, cast: Cast) -> None:
    unknown = "00000000-0000-4000-8000-000000000000"
    for who in ("client", "ops"):
        response = await client.get(f"/api/v1/projects/{unknown}", headers=_headers(cast, who))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "project_not_found"


async def test_suspended_member_is_refused(client: AsyncClient, cast: Cast, db_session: AsyncSession) -> None:
    cast.people["contractor"].status = "suspended"
    await db_session.flush()
    response = await client.get(f"/api/v1/projects/{cast.project.id}", headers=_headers(cast, "contractor"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_suspended"
