"""Public API of geo: polygon parsing and geofence checks with PostGIS. Owner: Abigail.

Other modules call geo only through this file. Every database function takes the session first.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.geo.polygon import ParsedPolygon, parse_polygon
from app.core.errors import AppError

__all__ = ["ParsedPolygon", "distance_to_fence", "inside_geofence", "parse_polygon"]

DEFAULT_BUFFER_M = 25.0  # GPS error allowance on top of the drawn fence

_INSIDE = text(
    """
    SELECT ST_Contains(
        ST_Buffer(geofence::geography, :buffer_m)::geometry,
        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
    )
    FROM sites WHERE id = :site_id
    """
)

_DISTANCE = text(
    """
    SELECT ST_Distance(geofence::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)
    FROM sites WHERE id = :site_id
    """
)


def _check_coords(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise AppError("invalid_coordinates", "Latitude or longitude is out of range.", 422)


async def inside_geofence(
    session: AsyncSession,
    site_id: uuid.UUID,
    lat: float,
    lon: float,
    buffer_m: float = DEFAULT_BUFFER_M,
) -> bool:
    """True if the point is inside the site fence or within `buffer_m` metres of it."""
    _check_coords(lat, lon)
    row = (
        await session.execute(_INSIDE, {"site_id": site_id, "lat": lat, "lon": lon, "buffer_m": buffer_m})
    ).first()
    if row is None:
        raise AppError("site_not_found", "This site does not exist.", 404)
    return bool(row[0])


async def distance_to_fence(session: AsyncSession, site_id: uuid.UUID, lat: float, lon: float) -> float:
    """Metres from the point to the fence edge (0.0 when the point is inside the fence)."""
    _check_coords(lat, lon)
    row = (await session.execute(_DISTANCE, {"site_id": site_id, "lat": lat, "lon": lon})).first()
    if row is None:
        raise AppError("site_not_found", "This site does not exist.", 404)
    return float(row[0])
