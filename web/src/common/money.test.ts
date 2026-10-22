import { describe, expect, it } from "vitest";

import { formatFxRate, formatMoney, minorDigits, roundDecimal, sumMinor } from "./money";

describe("formatMoney", () => {
  it("shows client currencies with pence/cents, as on the designs", () => {
    expect(formatMoney(160000, "GBP")).toBe("£1,600.00");
    expect(formatMoney(387516, "GBP")).toBe("£3,875.16");
    expect(formatMoney(160000, "USD")).toBe("$1,600.00");
    expect(formatMoney(160000, "EUR")).toBe("€1,600.00");
  });

  it("shows naira without kobo unless there are kobo", () => {
    expect(formatMoney(1053000000, "NGN")).toBe("₦10,530,000");
    expect(formatMoney(1053000050, "NGN")).toBe("₦10,530,000.50");
  });

  it("rounds estimates to whole units half away from zero", () => {
    expect(formatMoney(387516, "GBP", { decimals: "whole" })).toBe("£3,875");
    expect(formatMoney(387550, "GBP", { decimals: "whole" })).toBe("£3,876");
    expect(formatMoney(-387550, "GBP", { decimals: "whole" })).toBe("-£3,876");
  });

  it("is exact above 2^53 when given a bigint", () => {
    expect(formatMoney(12345678901234567890n, "NGN")).toBe("₦123,456,789,012,345,678.90");
  });

  it("refuses fractional or unsafe numbers instead of guessing", () => {
    expect(() => formatMoney(12.5, "GBP")).toThrow(TypeError);
    expect(() => formatMoney(Number.MAX_SAFE_INTEGER + 2, "NGN")).toThrow(TypeError);
  });

  it("knows each currency's minor digits", () => {
    expect(minorDigits("GBP")).toBe(2);
    expect(minorDigits("NGN")).toBe(2);
    expect(minorDigits("JPY")).toBe(0);
  });
});

describe("fx rates", () => {
  it("rounds decimal strings without floats", () => {
    expect(roundDecimal("1950.0000000000", 2)).toBe("1950.00");
    expect(roundDecimal("1962.4950000000", 2)).toBe("1962.50");
    expect(roundDecimal("1962.4949999999", 2)).toBe("1962.49");
    expect(roundDecimal("0.005", 2)).toBe("0.01");
    expect(() => roundDecimal("1e3", 2)).toThrow(TypeError);
  });

  it("formats the recorded rate as on the designs", () => {
    expect(formatFxRate("1950.0000000000", "GBP")).toBe("£1 = ₦1,950.00");
    expect(formatFxRate("1962.5", "GBP")).toBe("£1 = ₦1,962.50");
    expect(formatFxRate("1580.25", "USD")).toBe("$1 = ₦1,580.25");
  });
});

describe("sumMinor", () => {
  it("adds one currency exactly", () => {
    expect(
      sumMinor(
        [
          { amount_minor: 1053000000, currency: "NGN" },
          { amount_minor: 819000000, currency: "NGN" },
        ],
        "NGN",
      ),
    ).toBe(1872000000n);
  });

  it("refuses to mix currencies", () => {
    expect(() => sumMinor([{ amount_minor: 1, currency: "GBP" }], "NGN")).toThrow(TypeError);
  });
});
