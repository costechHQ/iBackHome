"""geo: GeoJSON parsing and geofence checks with PostGIS.

Owner: Abigail (only Abigail edits this folder).
Spec: FR-04, FR-08. See docs and the Backend Tasks doc for the day-by-day checklist.

Other features use only these names:

    from app.base import geo
    parsed = geo.parse_polygon(geojson)                     # no DB; raises AppError 422 if invalid
    ok = await geo.inside_geofence(session, site_id, lat, lon)  # 25 m buffer by default
    metres = await geo.distance_to_fence(session, site_id, lat, lon)
"""

from app.base.geo.polygone import ParsedPolygon, parse_polygon
from app.base.geo.queries import distance_to_fence, inside_geofence

__all__ = ["ParsedPolygon", "distance_to_fence", "inside_geofence", "parse_polygon"]
