"""Public API of geo: polygon parsing and geofence checks with PostGIS. Owner: Abigail.

Other modules call geo only through this file. Every database function takes the session first.

geo never reads the `sites` table (it belongs to projects). The caller looks up the site's
geofence (projects.service.get_geofence) and passes it in as an EWKT string such as
"SRID=4326;POLYGON((lon lat, ...))", the format `ParsedPolygon.ewkt` and PostGIS ST_AsEWKT() produce.
"""

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.geo.polygon import SRID, ParsedPolygon, parse_polygon
from app.core.errors import AppError

__all__ = ["ParsedPolygon", "distance_to_fence", "inside_geofence", "parse_polygon"]

DEFAULT_BUFFER_M = 25.0  # GPS error allowance on top of the drawn fence

_INSIDE = text(
    """
    SELECT ST_Contains(
        ST_Buffer(ST_GeomFromEWKT(:fence)::geography, :buffer_m)::geometry,
        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
    )
    """
)

_DISTANCE = text(
    """
    SELECT ST_Distance(
        ST_GeomFromEWKT(:fence)::geography,
        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
    )
    """
)

_FENCE_TYPE = text("SELECT GeometryType(ST_GeomFromEWKT(:fence)), ST_SRID(ST_GeomFromEWKT(:fence))")


def _invalid_geofence() -> AppError:
    return AppError("invalid_geofence", f"The geofence must be an EWKT Polygon with SRID {SRID}.", 422)


def _check_coords(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise AppError("invalid_coordinates", "Latitude or longitude is out of range.", 422)


async def _check_fence(session: AsyncSession, geofence_ewkt: str) -> None:
    """Reject anything PostGIS can't parse, or that isn't a Polygon with SRID 4326."""
    # A failed statement aborts the transaction, so test it inside a savepoint.
    try:
        async with session.begin_nested():
            row = (await session.execute(_FENCE_TYPE, {"fence": geofence_ewkt})).one()
    except DBAPIError as exc:
        raise _invalid_geofence() from exc
    if row[0] != "POLYGON" or row[1] != SRID:
        raise _invalid_geofence()


async def inside_geofence(
    session: AsyncSession,
    geofence_ewkt: str,
    lat: float,
    lon: float,
    buffer_m: float = DEFAULT_BUFFER_M,
) -> bool:
    """True if the point is inside the fence or within `buffer_m` metres of it."""
    _check_coords(lat, lon)
    await _check_fence(session, geofence_ewkt)
    row = (
        await session.execute(_INSIDE, {"fence": geofence_ewkt, "lat": lat, "lon": lon, "buffer_m": buffer_m})
    ).one()
    return bool(row[0])


async def distance_to_fence(session: AsyncSession, geofence_ewkt: str, lat: float, lon: float) -> float:
    """Metres from the point to the fence edge (0.0 when the point is inside the fence)."""
    _check_coords(lat, lon)
    await _check_fence(session, geofence_ewkt)
    row = (await session.execute(_DISTANCE, {"fence": geofence_ewkt, "lat": lat, "lon": lon})).one()
    return float(row[0])
