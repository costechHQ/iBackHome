import { describe, expect, it } from "vitest";

import { COMMON_ISO, COUNTRIES, countryByIso, searchCountries } from "@/common/countries";

import { clock, dialOf, maskIdentifier, phoneIdentifier, secondsUntil } from "./otp";

describe("phone numbers for the backend", () => {
  it("drops the national trunk 0 and adds the calling code", () => {
    expect(phoneIdentifier("44", "07700 900482")).toBe("+447700900482");
    expect(phoneIdentifier("44", "7700 900 482")).toBe("+447700900482");
    expect(phoneIdentifier("234", "0803 123 4567")).toBe("+2348031234567");
  });

  it("keeps a number typed with its own +", () => {
    expect(phoneIdentifier("44", "+234 803 000 0001")).toBe("+2348030000001");
  });
});

describe("the code step", () => {
  it("masks the number like the design and leaves an email alone", () => {
    expect(maskIdentifier("+447700900482")).toBe("+44 7700 ••• 482");
    expect(maskIdentifier("+2348030000001")).toBe("+234 8030 ••• 001");
    expect(maskIdentifier("adaeze@example.com")).toBe("adaeze@example.com");
  });

  it("finds the longest calling code that matches", () => {
    expect(dialOf("+12025550123")).toBe("1");
    expect(dialOf("+353871234567")).toBe("353");
  });

  it("counts down in m:ss, never below zero", () => {
    expect(clock(272)).toBe("4:32");
    expect(clock(29.2)).toBe("0:30");
    expect(clock(-3)).toBe("0:00");
    expect(secondsUntil(10_000, 4_000)).toBe(6);
    expect(secondsUntil(null, 4_000)).toBe(0);
  });
});

describe("the country list", () => {
  it("has unique countries, every common one, and digits-only codes", () => {
    expect(new Set(COUNTRIES.map((c) => c.iso)).size).toBe(COUNTRIES.length);
    for (const iso of COMMON_ISO) expect(countryByIso(iso)).toBeDefined();
    for (const c of COUNTRIES) expect(c.dial).toMatch(/^\d{1,3}$/);
  });

  it("searches by name, ISO code or calling code", () => {
    expect(searchCountries("niger").map((c) => c.iso)).toEqual(["NE", "NG"]);
    expect(searchCountries("gb").map((c) => c.iso)).toEqual(["GB"]);
    expect(searchCountries("+234").map((c) => c.iso)).toEqual(["NG"]);
  });
});
