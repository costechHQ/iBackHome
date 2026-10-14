"""PUT /projects/{id}/site, and the geofence other features read through service.py (FR-04)."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.geo import service as geo
from app.core.errors import AppError
from app.features.projects import service
from app.features.projects.models import Site
from app.features.projects.schemas import Pin, SiteSet
from app.features.projects.tests.factories import (
    FENCE,
    INSIDE,
    OUTSIDE,
    audit_entries,
    bearer,
    make_project,
    make_user,
)

# A second, larger fence about 1 km east, for "replace the site".
OTHER_FENCE: dict[str, Any] = {
    "type": "Polygon",
    "coordinates": [
        [[7.5230, 6.4480], [7.5240, 6.4480], [7.5240, 6.4490], [7.5230, 6.4490], [7.5230, 6.4480]]
    ],
}
OTHER_INSIDE = {"lat": 6.4485, "lon": 7.5235}


async def _put(
    client: AsyncClient, project_id: uuid.UUID, headers: dict[str, str], body: dict[str, Any]
) -> Any:
    return await client.put(f"/api/v1/projects/{project_id}/site", json=body, headers=headers)


async def test_client_sets_the_site(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    response = await _put(client, project.id, bearer(owner), {"location": INSIDE, "geofence": FENCE})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["location"] == INSIDE
    assert body["geofence"]["coordinates"] == FENCE["coordinates"]


async def test_geofence_is_stored_as_srid_4326_polygon_with_gist_index(db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    await service.set_site(db_session, owner, project.id, SiteSet(location=Pin(**INSIDE), geofence=FENCE))
    row = (
        await db_session.execute(
            select(
                func.GeometryType(Site.geofence),
                func.ST_SRID(Site.geofence),
                func.GeometryType(Site.location),
                func.ST_SRID(Site.location),
            ).where(Site.project_id == project.id)
        )
    ).one()
    assert tuple(row) == ("POLYGON", 4326, "POINT", 4326)
    index = await db_session.scalar(func.pg_get_indexdef(func.to_regclass("ix_sites_geofence")).select())
    assert index is not None and "USING gist (geofence)" in index


async def test_get_geofence_round_trips_through_geo(db_session: AsyncSession) -> None:
    """What Abigail's evidence checks do: fetch the EWKT, then ask geo whether a capture is inside."""
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    await service.set_site(db_session, owner, project.id, SiteSet(location=Pin(**INSIDE), geofence=FENCE))
    site_id = await db_session.scalar(select(Site.id).where(Site.project_id == project.id))
    assert site_id is not None

    by_site = await service.get_geofence(db_session, site_id)
    by_project = await service.get_project_geofence(db_session, project.id)
    assert by_site == by_project
    assert by_site.startswith("SRID=4326;POLYGON((")
    assert await geo.inside_geofence(db_session, by_site, INSIDE["lat"], INSIDE["lon"])
    assert not await geo.inside_geofence(db_session, by_site, OUTSIDE["lat"], OUTSIDE["lon"])


async def test_unknown_site_and_unset_site_are_404(db_session: AsyncSession) -> None:
    project = await make_project(db_session)
    with pytest.raises(AppError) as caught:
        await service.get_geofence(db_session, uuid.uuid4())
    assert (caught.value.code, caught.value.status_code) == ("site_not_found", 404)
    with pytest.raises(AppError) as caught:
        await service.get_project_geofence(db_session, project.id)
    assert (caught.value.code, caught.value.status_code) == ("site_not_set", 404)


async def test_pin_outside_the_geofence_is_422(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    response = await _put(client, project.id, bearer(owner), {"location": OUTSIDE, "geofence": FENCE})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "pin_outside_geofence"
    assert await service.get_site(db_session, project.id) is None


@pytest.mark.parametrize(
    "geofence",
    [
        {"type": "Point", "coordinates": [7.5139, 6.4483]},
        {
            "type": "Polygon",
            "coordinates": [[[7.5135, 6.4480], [7.5143, 6.4480], [7.5143, 6.4487]]],
        },  # not closed
        {  # a bow tie: edges cross
            "type": "Polygon",
            "coordinates": [
                [[7.5135, 6.4480], [7.5143, 6.4487], [7.5143, 6.4480], [7.5135, 6.4487], [7.5135, 6.4480]]
            ],
        },
        {  # latitude 97.5 doesn't exist
            "type": "Polygon",
            "coordinates": [[[6.4480, 97.5135], [6.4480, 97.5143], [6.4487, 97.5143], [6.4480, 97.5135]]],
        },
        {  # too small: about 1 m2
            "type": "Polygon",
            "coordinates": [
                [
                    [7.51390, 6.44830],
                    [7.51391, 6.44830],
                    [7.51391, 6.44831],
                    [7.51390, 6.44831],
                    [7.51390, 6.44830],
                ]
            ],
        },
    ],
)
async def test_invalid_geofence_is_422(
    client: AsyncClient, db_session: AsyncSession, geofence: dict[str, Any]
) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    response = await _put(client, project.id, bearer(owner), {"location": INSIDE, "geofence": geofence})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_geofence"


@pytest.mark.parametrize("location", [{"lat": 91, "lon": 7.5}, {"lat": 6.4, "lon": -181}, {"lat": 6.4}])
async def test_invalid_pin_is_422(
    client: AsyncClient, db_session: AsyncSession, location: dict[str, Any]
) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    response = await _put(client, project.id, bearer(owner), {"location": location, "geofence": FENCE})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_a_geojson_feature_is_accepted(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    feature = {"type": "Feature", "properties": {}, "geometry": FENCE}
    response = await _put(client, project.id, bearer(owner), {"location": INSIDE, "geofence": feature})
    assert response.status_code == 200, response.text


async def test_second_put_replaces_the_site_and_audits_both(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session, "client")
    ops = await make_user(db_session, "ops")
    project = await make_project(db_session, client=owner)
    assert (
        await _put(client, project.id, bearer(owner), {"location": INSIDE, "geofence": FENCE})
    ).status_code == 200
    second = await _put(client, project.id, bearer(ops), {"location": OTHER_INSIDE, "geofence": OTHER_FENCE})
    assert second.status_code == 200, second.text

    count = await db_session.scalar(
        select(func.count()).select_from(Site).where(Site.project_id == project.id)
    )
    assert count == 1
    site = await service.get_site(db_session, project.id)
    assert site is not None and site.location == Pin(**OTHER_INSIDE)

    site_id = await db_session.scalar(select(Site.id).where(Site.project_id == project.id))
    assert site_id is not None
    entries = [e for e in await audit_entries(db_session, site_id) if e.action == "site.set"]
    assert len(entries) == 2
    first, replaced = sorted(entries, key=lambda e: e.before is not None)
    assert first.actor_id == owner.id and first.before is None
    assert replaced.actor_id == ops.id
    assert replaced.before is not None and replaced.before["location"] == "SRID=4326;POINT(7.5139 6.4483)"
    assert replaced.after is not None and replaced.after["location"] == "SRID=4326;POINT(7.5235 6.4485)"
    assert replaced.after["project_id"] == str(project.id)


async def test_same_idempotency_key_replays(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await make_user(db_session, "client")
    project = await make_project(db_session, client=owner)
    headers = bearer(owner) | {"Idempotency-Key": "site-1"}
    first = await _put(client, project.id, headers, {"location": INSIDE, "geofence": FENCE})
    second = await _put(client, project.id, headers, {"location": INSIDE, "geofence": FENCE})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    site_id = await db_session.scalar(select(Site.id).where(Site.project_id == project.id))
    assert site_id is not None
    assert len(await audit_entries(db_session, site_id)) == 1


async def test_service_checks_role_and_membership_itself(db_session: AsyncSession) -> None:
    """The rules live in service.py, so a new route can't skip them."""
    contractor = await make_user(db_session, "contractor")
    stranger = await make_user(db_session, "client")
    project = await make_project(db_session, contractor=contractor)
    data = SiteSet(location=Pin(**INSIDE), geofence=FENCE)
    with pytest.raises(AppError) as caught:
        await service.set_site(db_session, contractor, project.id, data)
    assert caught.value.code == "forbidden_role"
    with pytest.raises(AppError) as caught:
        await service.set_site(db_session, stranger, project.id, data)
    assert caught.value.code == "not_project_member"
