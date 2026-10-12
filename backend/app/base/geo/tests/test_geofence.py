import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.geo import service as geo
from app.core.errors import AppError

# A ~100 m x 100 m site in Enugu; latitude 6.4600 is its north edge.
SITE_SW = (7.5000, 6.4590)  # (lon, lat)
SITE_NE = (7.5009, 6.4600)
M_PER_DEG_LAT = 111_195.0

SQUARE = {
    "type": "Polygon",
    "coordinates": [
        [
            [SITE_SW[0], SITE_SW[1]],
            [SITE_NE[0], SITE_SW[1]],
            [SITE_NE[0], SITE_NE[1]],
            [SITE_SW[0], SITE_NE[1]],
            [SITE_SW[0], SITE_SW[1]],
        ]
    ],
}
FENCE = geo.parse_polygon(SQUARE).ewkt
CENTER_LON = (SITE_SW[0] + SITE_NE[0]) / 2
CENTER_LAT = (SITE_SW[1] + SITE_NE[1]) / 2
NORTH_EDGE_LAT = SITE_NE[1]


def north_of_edge(metres: float) -> float:
    return NORTH_EDGE_LAT + metres / M_PER_DEG_LAT


async def test_inside_point_accepted(db_session: AsyncSession) -> None:
    assert await geo.inside_geofence(db_session, FENCE, 6.4595, CENTER_LON) is True


async def test_round_trip_centre_is_inside(db_session: AsyncSession) -> None:
    fence = geo.parse_polygon(SQUARE).ewkt
    assert await geo.inside_geofence(db_session, fence, CENTER_LAT, CENTER_LON) is True


async def test_point_on_edge_accepted(db_session: AsyncSession) -> None:
    assert await geo.inside_geofence(db_session, FENCE, NORTH_EDGE_LAT, CENTER_LON) is True


async def test_20m_outside_accepted(db_session: AsyncSession) -> None:
    assert await geo.inside_geofence(db_session, FENCE, north_of_edge(20), CENTER_LON) is True


async def test_50m_outside_rejected(db_session: AsyncSession) -> None:
    assert await geo.inside_geofence(db_session, FENCE, north_of_edge(50), CENTER_LON) is False


async def test_custom_buffer(db_session: AsyncSession) -> None:
    lat = north_of_edge(20)
    assert await geo.inside_geofence(db_session, FENCE, lat, CENTER_LON, buffer_m=10) is False
    assert await geo.inside_geofence(db_session, FENCE, lat, CENTER_LON, buffer_m=30) is True


async def test_distance_inside_is_zero(db_session: AsyncSession) -> None:
    assert await geo.distance_to_fence(db_session, FENCE, 6.4595, CENTER_LON) == 0


async def test_distance_outside(db_session: AsyncSession) -> None:
    metres = await geo.distance_to_fence(db_session, FENCE, north_of_edge(50), CENTER_LON)
    assert metres == pytest.approx(50, abs=1)


async def test_bad_coordinates_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as err:
        await geo.inside_geofence(db_session, FENCE, 123.0, CENTER_LON)
    assert err.value.code == "invalid_coordinates"
    assert err.value.status_code == 422


async def test_unparseable_geofence_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as err:
        await geo.inside_geofence(db_session, "not a polygon", CENTER_LAT, CENTER_LON)
    assert err.value.code == "invalid_geofence"
    assert err.value.status_code == 422


async def test_non_polygon_geofence_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as err:
        await geo.distance_to_fence(db_session, "SRID=4326;POINT(7.5 6.459)", CENTER_LAT, CENTER_LON)
    assert err.value.code == "invalid_geofence"


async def test_wrong_srid_geofence_rejected(db_session: AsyncSession) -> None:
    wrong = FENCE.replace("SRID=4326", "SRID=3857")
    with pytest.raises(AppError) as err:
        await geo.inside_geofence(db_session, wrong, CENTER_LAT, CENTER_LON)
    assert err.value.code == "invalid_geofence"
