from typing import Any

import pytest

from app.base import geo
from app.core.errors import AppError

# ~100 m x 100 m square in Enugu
RING = [[7.5, 6.459], [7.5009, 6.459], [7.5009, 6.46], [7.5, 6.46], [7.5, 6.459]]


def polygon(ring: list[list[float]]) -> dict[str, Any]:
    return {"type": "Polygon", "coordinates": [ring]}


def code_of(geojson: Any) -> str:
    with pytest.raises(AppError) as err:
        geo.parse_polygon(geojson)
    assert err.value.status_code == 422
    return err.value.code


def test_valid_polygon() -> None:
    parsed = geo.parse_polygon(polygon(RING))
    assert 11_000 < parsed.area_m2 < 11_100
    assert parsed.ewkt.startswith("SRID=4326;POLYGON((7.5 6.459, 7.5009 6.459")
    assert parsed.centroid == pytest.approx((7.50045, 6.4595), abs=1e-6)


def test_feature_wrapper_accepted() -> None:
    parsed = geo.parse_polygon({"type": "Feature", "properties": {}, "geometry": polygon(RING)})
    assert parsed.ring[0] == parsed.ring[-1]


def test_unclosed_ring_rejected() -> None:
    assert code_of(polygon(RING[:-1])) == "invalid_geofence"


def test_too_few_points_rejected() -> None:
    assert code_of(polygon([[7.5, 6.459], [7.5009, 6.459], [7.5, 6.459]])) == "invalid_geofence"


def test_duplicate_points_rejected() -> None:
    assert code_of(polygon([[7.5, 6.459], [7.5, 6.459], [7.5, 6.459], [7.5, 6.459]])) == "invalid_geofence"


def test_wrong_type_rejected() -> None:
    assert code_of({"type": "Point", "coordinates": [7.5, 6.459]}) == "invalid_geofence"
    assert code_of("not geojson") == "invalid_geofence"


def test_out_of_range_coordinates_rejected() -> None:
    bad = [[7.5, 96.0], [7.5009, 96.0], [7.5009, 96.001], [7.5, 96.0]]
    assert code_of(polygon(bad)) == "invalid_geofence"


def test_tiny_area_rejected() -> None:
    tiny = [[7.5, 6.459], [7.500001, 6.459], [7.500001, 6.459001], [7.5, 6.459]]
    assert code_of(polygon(tiny)) == "invalid_geofence"


def test_huge_area_rejected() -> None:
    huge = [[7.0, 6.0], [8.0, 6.0], [8.0, 7.0], [7.0, 7.0], [7.0, 6.0]]
    assert code_of(polygon(huge)) == "invalid_geofence"


def test_bowtie_rejected() -> None:
    bowtie = [[7.5, 6.459], [7.5009, 6.46], [7.5009, 6.459], [7.5, 6.46], [7.5, 6.459]]
    assert code_of(polygon(bowtie)) == "invalid_geofence"


def test_holes_rejected() -> None:
    assert code_of({"type": "Polygon", "coordinates": [RING, RING]}) == "invalid_geofence"
