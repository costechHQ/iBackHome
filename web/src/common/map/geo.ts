// Site geometry for the geofence map (components.md, Geofence map): converting between the map's [lat, lon]
// corners and the API's GeoJSON Polygon ([lon, lat], closed ring), checking the pin is inside, and the 25 m
// tolerance band drawn around the boundary. The server decides inside/outside (PostGIS); these only guide.

export type LatLon = { lat: number; lon: number };

export const TOLERANCE_METRES = 25;

const EARTH_RADIUS_M = 6_371_000;
const rad = (deg: number) => (deg * Math.PI) / 180;

/** Great-circle distance in metres. */
export function metresBetween(a: LatLon, b: LatLon): number {
  const dLat = rad(b.lat - a.lat);
  const dLon = rad(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

/** Ray casting; fine at site scale (a few hundred metres). */
export function insidePolygon(point: LatLon, corners: readonly LatLon[]): boolean {
  let inside = false;
  for (let i = 0, j = corners.length - 1; i < corners.length; j = i++) {
    const a = corners[i]!;
    const b = corners[j]!;
    const crosses =
      a.lat > point.lat !== b.lat > point.lat &&
      point.lon < ((b.lon - a.lon) * (point.lat - a.lat)) / (b.lat - a.lat) + a.lon;
    if (crosses) inside = !inside;
  }
  return inside;
}

/** The API's GeoJSON Polygon: [lon, lat] pairs, the ring closed by repeating the first corner. */
export function toGeoJson(corners: readonly LatLon[]): { type: "Polygon"; coordinates: number[][][] } {
  const ring = corners.map((c) => [round6(c.lon), round6(c.lat)]);
  if (ring.length) ring.push([...ring[0]!]);
  return { type: "Polygon", coordinates: [ring] };
}

/** Corners from a stored GeoJSON Polygon (the closing corner dropped); [] if it isn't one. */
export function fromGeoJson(geojson: unknown): LatLon[] {
  const g = geojson as { type?: string; coordinates?: unknown };
  if (g?.type !== "Polygon" || !Array.isArray(g.coordinates) || !Array.isArray(g.coordinates[0])) return [];
  const ring = (g.coordinates[0] as unknown[]).filter(
    (p): p is [number, number] => Array.isArray(p) && typeof p[0] === "number" && typeof p[1] === "number",
  );
  const corners = ring.map(([lon, lat]) => ({ lat, lon }));
  const first = corners[0];
  const last = corners.at(-1);
  if (corners.length > 1 && first && last && first.lat === last.lat && first.lon === last.lon) corners.pop();
  return corners;
}

function centroid(corners: readonly LatLon[]): LatLon {
  const n = corners.length;
  return {
    lat: corners.reduce((s, c) => s + c.lat, 0) / n,
    lon: corners.reduce((s, c) => s + c.lon, 0) / n,
  };
}

/**
 * The tolerance band, drawn: each corner pushed `metres` further from the middle. An approximation for the
 * picture only (the server buffers the real shape).
 */
export function toleranceRing(corners: readonly LatLon[], metres = TOLERANCE_METRES): LatLon[] {
  if (corners.length < 3) return [];
  const mid = centroid(corners);
  return corners.map((c) => {
    const d = metresBetween(mid, c);
    if (d === 0) return c;
    const k = (d + metres) / d;
    return { lat: mid.lat + (c.lat - mid.lat) * k, lon: mid.lon + (c.lon - mid.lon) * k };
  });
}

/** Roughly how far (metres) a point is from the nearest corner, for "the pin is N m outside". */
export function nearestCornerMetres(point: LatLon, corners: readonly LatLon[]): number {
  return Math.min(...corners.map((c) => metresBetween(point, c)));
}

function round6(n: number): number {
  return Math.round(n * 1e6) / 1e6;
}
