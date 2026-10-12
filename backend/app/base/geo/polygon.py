"""Validate a GeoJSON polygon before it is saved as a site geofence (pure Python, no database)."""

import math
from dataclasses import dataclass
from typing import Any

from app.core.errors import AppError

SRID = 4326
MIN_AREA_M2 = 25.0  # smaller than a parking space is almost certainly a mistake
MAX_AREA_M2 = 5_000_000.0  # 5 km2: bigger than any single build site we expect
_EARTH_RADIUS_M = 6_371_008.8

Point = tuple[float, float]  # (lon, lat), GeoJSON order


@dataclass(frozen=True)
class ParsedPolygon:
    ring: list[Point]  # closed: first point == last point
    area_m2: float
    centroid: Point  # (lon, lat)

    @property
    def wkt(self) -> str:
        return "POLYGON((" + ", ".join(f"{lon} {lat}" for lon, lat in self.ring) + "))"

    @property
    def ewkt(self) -> str:
        """Ready for `ST_GeomFromEWKT(:ewkt)` when saving to a geometry(Polygon, 4326) column."""
        return f"SRID={SRID};{self.wkt}"

    @property
    def geojson(self) -> dict[str, Any]:
        return {"type": "Polygon", "coordinates": [[list(p) for p in self.ring]]}


def _bad(message: str) -> AppError:
    return AppError("invalid_geofence", message, 422)


def parse_polygon(geojson: dict[str, Any]) -> ParsedPolygon:
    """Check a GeoJSON Polygon (or a Feature holding one) and return it normalised.

    Rules: one closed ring of at least 3 distinct points, valid WGS84 (SRID 4326) coordinates in
    [lon, lat] order, no self-crossing, and an area between 25 m2 and 5 km2.
    Raises AppError("invalid_geofence", ..., 422) on anything else.
    """
    if not isinstance(geojson, dict):
        raise _bad("Geofence must be a GeoJSON object.")
    if geojson.get("type") == "Feature":
        geojson = geojson.get("geometry") or {}
    if geojson.get("type") != "Polygon":
        raise _bad("Geofence must be a GeoJSON Polygon.")

    rings = geojson.get("coordinates")
    if not isinstance(rings, list) or not rings:
        raise _bad("Polygon has no coordinates.")
    if len(rings) > 1:
        raise _bad("Polygons with holes are not supported; send a single outer ring.")

    ring = _read_ring(rings[0])
    if ring[0] != ring[-1]:
        raise _bad("The polygon ring is not closed: the last point must equal the first.")
    if len(set(ring[:-1])) < 3:
        raise _bad("A geofence needs at least 3 distinct points.")
    if _self_intersects(ring):
        raise _bad("The polygon edges cross each other.")

    area, centroid = _area_and_centroid(ring)
    if area < MIN_AREA_M2:
        raise _bad(f"The geofence is too small ({area:.1f} m2); the minimum is {MIN_AREA_M2:.0f} m2.")
    if area > MAX_AREA_M2:
        raise _bad(f"The geofence is too large ({area / 1e6:.2f} km2); the maximum is 5 km2.")
    return ParsedPolygon(ring=ring, area_m2=area, centroid=centroid)


def _read_ring(raw: Any) -> list[Point]:
    if not isinstance(raw, list):
        raise _bad("The polygon ring must be a list of [lon, lat] points.")
    ring: list[Point] = []
    for position in raw:
        if (
            not isinstance(position, list | tuple)
            or len(position) < 2
            or not all(isinstance(v, int | float) and not isinstance(v, bool) for v in position[:2])
        ):
            raise _bad("Every point must be a [lon, lat] pair of numbers.")
        lon, lat = float(position[0]), float(position[1])
        if not (math.isfinite(lon) and math.isfinite(lat)) or abs(lon) > 180 or abs(lat) > 90:
            raise _bad(f"Point [{lon}, {lat}] is not a valid longitude/latitude (SRID {SRID}).")
        ring.append((lon, lat))
    if len(ring) < 4:  # 3 corners + the closing point
        raise _bad("A geofence needs at least 3 distinct points (4 positions with the closing one).")
    return ring


def _project(ring: list[Point]) -> list[Point]:
    """Local flat projection in metres around the first point (fine at site scale)."""
    lon0, lat0 = ring[0]
    kx = math.radians(1) * _EARTH_RADIUS_M * math.cos(math.radians(lat0))
    ky = math.radians(1) * _EARTH_RADIUS_M
    return [((lon - lon0) * kx, (lat - lat0) * ky) for lon, lat in ring]


def _area_and_centroid(ring: list[Point]) -> tuple[float, Point]:
    xy = _project(ring)
    twice_area = 0.0
    for (x1, y1), (x2, y2) in zip(xy, xy[1:], strict=False):
        twice_area += x1 * y2 - x2 * y1
    centroid = (
        sum(p[0] for p in ring[:-1]) / (len(ring) - 1),
        sum(p[1] for p in ring[:-1]) / (len(ring) - 1),
    )
    return abs(twice_area) / 2, centroid


def _cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_cross(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    d1, d2 = _cross(p3, p4, p1), _cross(p3, p4, p2)
    d3, d4 = _cross(p1, p2, p3), _cross(p1, p2, p4)
    return d1 * d2 < 0 and d3 * d4 < 0


def _self_intersects(ring: list[Point]) -> bool:
    edges = list(zip(ring, ring[1:], strict=False))
    n = len(edges)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:  # first and last edge share the closing point
                continue
            if _segments_cross(*edges[i], *edges[j]):
                return True
    return False
