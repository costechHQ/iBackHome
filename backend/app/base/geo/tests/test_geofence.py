import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.geo import service as geo
from app.base.geo.tests.conftest import M_PER_DEG_LAT, SITE_NE, SITE_SW
from app.core.errors import AppError

CENTER_LON = (SITE_SW[0] + SITE_NE[0]) / 2
NORTH_EDGE_LAT = SITE_NE[1]


def north_of_edge(metres: float) -> float:
    return NORTH_EDGE_LAT + metres / M_PER_DEG_LAT


async def test_inside_point_accepted(session: AsyncSession, site_id: uuid.UUID) -> None:
    assert await geo.inside_geofence(session, site_id, 6.4595, CENTER_LON) is True


async def test_point_on_edge_accepted(session: AsyncSession, site_id: uuid.UUID) -> None:
    assert await geo.inside_geofence(session, site_id, NORTH_EDGE_LAT, CENTER_LON) is True


async def test_20m_outside_accepted(session: AsyncSession, site_id: uuid.UUID) -> None:
    assert await geo.inside_geofence(session, site_id, north_of_edge(20), CENTER_LON) is True


async def test_50m_outside_rejected(session: AsyncSession, site_id: uuid.UUID) -> None:
    assert await geo.inside_geofence(session, site_id, north_of_edge(50), CENTER_LON) is False


async def test_custom_buffer(session: AsyncSession, site_id: uuid.UUID) -> None:
    lat = north_of_edge(20)
    assert await geo.inside_geofence(session, site_id, lat, CENTER_LON, buffer_m=10) is False
    assert await geo.inside_geofence(session, site_id, lat, CENTER_LON, buffer_m=30) is True


async def test_distance_inside_is_zero(session: AsyncSession, site_id: uuid.UUID) -> None:
    assert await geo.distance_to_fence(session, site_id, 6.4595, CENTER_LON) == 0


async def test_distance_outside(session: AsyncSession, site_id: uuid.UUID) -> None:
    metres = await geo.distance_to_fence(session, site_id, north_of_edge(50), CENTER_LON)
    assert metres == pytest.approx(50, abs=1)


async def test_unknown_site_is_404(session: AsyncSession) -> None:
    with pytest.raises(AppError) as err:
        await geo.inside_geofence(session, uuid.uuid4(), 6.4595, CENTER_LON)
    assert err.value.status_code == 404
    assert err.value.code == "site_not_found"


async def test_bad_coordinates_rejected(session: AsyncSession, site_id: uuid.UUID) -> None:
    with pytest.raises(AppError) as err:
        await geo.inside_geofence(session, site_id, 123.0, CENTER_LON)
    assert err.value.code == "invalid_coordinates"
