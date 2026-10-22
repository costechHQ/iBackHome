import { describe, expect, it } from "vitest";

import { fromGeoJson, insidePolygon, metresBetween, toGeoJson, toleranceRing } from "./geo";

// A square about 90 m a side in Enugu (like seed.py's square_fence).
const pin = { lat: 6.4483, lon: 7.5139 };
const h = 0.0004;
const square = [
  { lat: pin.lat - h, lon: pin.lon - h },
  { lat: pin.lat - h, lon: pin.lon + h },
  { lat: pin.lat + h, lon: pin.lon + h },
  { lat: pin.lat + h, lon: pin.lon - h },
];

describe("site geometry", () => {
  it("measures distance in metres", () => {
    expect(metresBetween(square[0]!, square[1]!)).toBeGreaterThan(85);
    expect(metresBetween(square[0]!, square[1]!)).toBeLessThan(92);
  });

  it("knows whether the pin is inside the boundary", () => {
    expect(insidePolygon(pin, square)).toBe(true);
    expect(insidePolygon({ lat: pin.lat + 0.001, lon: pin.lon }, square)).toBe(false);
  });

  it("writes the API's GeoJSON ([lon, lat], closed ring) and reads it back", () => {
    const g = toGeoJson(square);
    expect(g.type).toBe("Polygon");
    expect(g.coordinates[0]).toHaveLength(5);
    expect(g.coordinates[0]![0]).toEqual([7.5135, 6.4479]);
    expect(g.coordinates[0]![4]).toEqual(g.coordinates[0]![0]);
    expect(fromGeoJson(g)).toEqual(square.map((c) => ({ lat: +c.lat.toFixed(6), lon: +c.lon.toFixed(6) })));
    expect(fromGeoJson({ type: "Point", coordinates: [1, 2] })).toEqual([]);
  });

  it("draws the tolerance band about 25 m outside each corner", () => {
    const ring = toleranceRing(square);
    expect(ring).toHaveLength(4);
    const mid = { lat: pin.lat, lon: pin.lon };
    const grew = metresBetween(mid, ring[0]!) - metresBetween(mid, square[0]!);
    expect(grew).toBeGreaterThan(24);
    expect(grew).toBeLessThan(26);
    expect(toleranceRing(square.slice(0, 2))).toEqual([]);
  });
});
