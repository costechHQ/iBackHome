import { describe, expect, it } from "vitest";

import { guessCountry, zoneLabel, zoneOptions } from "./places";

const summer = new Date("2026-07-01T12:00:00Z");
const winter = new Date("2026-01-15T12:00:00Z");

describe("time zones", () => {
  it("labels zones like the design", () => {
    expect(zoneLabel("Europe/London", summer)).toBe("London (BST, UTC+1)");
    expect(zoneLabel("Europe/London", winter)).toMatch(/^London \((GMT, )?UTC\+0\)$/);
    expect(zoneLabel("Africa/Lagos", summer)).toMatch(/^Lagos \((WAT, )?UTC\+1\)$/);
    expect(zoneLabel("UTC")).toBe("UTC");
  });

  it("offers every zone once, including the ones clients use", () => {
    const values = zoneOptions(summer).map((z) => z.value);
    expect(new Set(values).size).toBe(values.length);
    expect(values).toEqual(
      expect.arrayContaining(["Europe/London", "America/New_York", "Africa/Lagos", "UTC"]),
    );
  });
});

describe("guessing the country", () => {
  it("uses the phone's country code, preferring the common countries", () => {
    expect(guessCountry("+447911123456")).toBe("GB");
    expect(guessCountry("+12025550123")).toBe("US");
    expect(guessCountry("+2348030000001")).toBe("NG");
  });

  it("falls back to the browser's region, else nothing", () => {
    expect(guessCountry(null, "en-IE")).toBe("IE");
    expect(guessCountry(null, "en")).toBeNull();
  });
});
