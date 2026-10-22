import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime, formatTime, formatUtc, viewerTimeZone, WAT } from "./time";

const NOW = new Date("2026-12-20T12:00:00Z");

describe("viewerTimeZone", () => {
  it("uses the client's own zone", () => {
    expect(viewerTimeZone({ role: "client", timezone: "Europe/London" })).toBe("Europe/London");
  });

  it("uses WAT for every Nigerian role, whatever their profile says", () => {
    for (const role of ["contractor", "supervisor", "supplier", "ops"]) {
      expect(viewerTimeZone({ role, timezone: "Europe/London" })).toBe(WAT);
    }
  });

  it("falls back to WAT for a client with a missing or invalid zone", () => {
    expect(viewerTimeZone({ role: "client", timezone: null })).toBe(WAT);
    expect(viewerTimeZone({ role: "client", timezone: "Mars/Olympus" })).toBe(WAT);
  });
});

describe("formatting", () => {
  const iso = "2026-12-14T09:12:00Z";

  it("shows a London client GMT in winter and BST in summer", () => {
    expect(formatTime(iso, "Europe/London")).toBe("09:12 GMT");
    expect(formatTime("2026-07-14T09:12:00Z", "Europe/London")).toBe("10:12 BST");
  });

  it("shows Nigerian roles WAT", () => {
    expect(formatTime(iso, WAT)).toBe("10:12 WAT");
    expect(formatDateTime("2027-01-08T07:10:00Z", WAT, new Date("2027-01-10T00:00:00Z"))).toBe(
      "Fri 8 Jan, 08:10 WAT",
    );
  });

  it("uses the viewer's date, not the UTC date, near midnight", () => {
    expect(formatDate("2026-12-14T23:30:00Z", WAT, NOW)).toBe("Tue 15 Dec");
    expect(formatDate("2026-12-14T23:30:00Z", "America/New_York", NOW)).toBe("Mon 14 Dec");
  });

  it("adds the year only for another year", () => {
    expect(formatDate(iso, "Europe/London", NOW)).toBe("Mon 14 Dec");
    expect(formatDate("2025-11-30T09:00:00Z", "Europe/London", NOW)).toBe("Sun 30 Nov 2025");
  });

  it("gives the UTC time for hover text", () => {
    expect(formatUtc(iso)).toBe("2026-12-14 09:12 UTC");
  });

  it("refuses something that isn't a date", () => {
    expect(() => formatTime("yesterday", WAT)).toThrow(TypeError);
  });
});

describe("zone labels", () => {
  it("spells London winter time GMT whatever the ICU build says", async () => {
    const { zoneLabel } = await import("./time");
    expect(zoneLabel("2026-12-14T09:12:00Z", "Europe/London")).toBe("GMT");
    expect(zoneLabel("2026-12-14T09:12:00Z", "UTC")).toMatch(/^(UTC|GMT)$/);
  });
});
