import { describe, expect, it } from "vitest";

import { missingSteps, stepsFor } from "./steps";

const done = { full_name: "Adaeze Okafor", country: "GB", consent_required: false };

describe("onboarding steps", () => {
  it("asks for consent first, then only what is missing", () => {
    expect(missingSteps({ role: "client", consent_required: true })).toEqual([
      "consent",
      "details",
      "location",
    ]);
    expect(missingSteps({ role: "client", ...done })).toEqual([]);
    expect(missingSteps({ role: "client", ...done, country: null })).toEqual(["location"]);
    expect(missingSteps({ role: "client", ...done, full_name: "  " })).toEqual(["details"]);
  });

  it("needs a contractor's payout account, unless it couldn't be checked", () => {
    expect(missingSteps({ role: "contractor", ...done }, false)).toEqual(["payout"]);
    expect(missingSteps({ role: "contractor", ...done }, true)).toEqual([]);
    expect(missingSteps({ role: "contractor", ...done }, null)).toEqual([]);
    // A contractor's country isn't asked for.
    expect(missingSteps({ role: "contractor", ...done, country: null }, true)).toEqual([]);
  });

  it("never onboards ops or roles without a web portal", () => {
    for (const role of ["ops", "supervisor", "supplier"]) {
      expect(stepsFor(role)).toEqual([]);
      expect(missingSteps({ role, consent_required: true }, false)).toEqual([]);
    }
  });
});
