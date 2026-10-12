"""geo: GeoJSON parsing and geofence checks with PostGIS.

Owner: Abigail (only Abigail edits this folder).
Spec: FR-04, FR-08. Other modules call geo only through service.py:

    from app.base.geo import service as geo
    parsed = geo.parse_polygon(geojson)                          # no DB; AppError 422 if invalid
    ok = await geo.inside_geofence(session, geofence_ewkt, lat, lon)   # 25 m buffer by default
    metres = await geo.distance_to_fence(session, geofence_ewkt, lat, lon)
"""
