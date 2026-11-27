import { describe, expect, it } from "vitest";

import {
  approvalBlockers,
  listText,
  openChecks,
  registrationRequired,
  specialtyLabel,
  summaryReady,
  type ContractorChecks,
} from "./contractors";

const NONE: ContractorChecks = {
  registration_verified: false,
  reference_1_verified: false,
  reference_2_verified: false,
};
const ALL: ContractorChecks = {
  registration_verified: true,
  reference_1_verified: true,
  reference_2_verified: true,
};
const SUMMARY = "Established Enugu builder with twelve years on residential work.";

describe("registrationRequired", () => {
  it("is needed only when a CAC or CORBON number was given", () => {
    expect(registrationRequired({ cac_rc_number: "RC1234567" })).toBe(true);
    expect(registrationRequired({ corbon_number: "CB-1" })).toBe(true);
    expect(registrationRequired({ cac_rc_number: null, corbon_number: null })).toBe(false);
    expect(registrationRequired({})).toBe(false);
  });
});

describe("openChecks", () => {
  it("lists the registration first when a number was given, then each reference", () => {
    expect(openChecks({ cac_rc_number: "RC1" }, NONE)).toEqual([
      "registration_verified",
      "reference_1_verified",
      "reference_2_verified",
    ]);
  });

  it("never asks for a registration nobody gave", () => {
    expect(openChecks({}, NONE)).toEqual(["reference_1_verified", "reference_2_verified"]);
  });

  it("is empty once everything required is ticked", () => {
    expect(openChecks({ cac_rc_number: "RC1" }, ALL)).toEqual([]);
    expect(openChecks({}, { ...NONE, reference_1_verified: true, reference_2_verified: true })).toEqual([]);
  });
});

describe("summaryReady", () => {
  it("needs at least 20 characters once trimmed", () => {
    expect(summaryReady("")).toBe(false);
    expect(summaryReady("   short   ")).toBe(false);
    expect(summaryReady(SUMMARY)).toBe(true);
  });
});

describe("approvalBlockers", () => {
  it("lists what still blocks approval in plain words", () => {
    const blockers = approvalBlockers({ cac_rc_number: "RC1" }, { ...NONE, reference_1_verified: true }, "");
    expect(blockers).toEqual([
      "Registration checked on the register",
      "Second reference confirmed by phone",
      "A profile summary of at least 20 characters",
    ]);
  });

  it("is empty when ops may approve", () => {
    expect(approvalBlockers({ cac_rc_number: "RC1" }, ALL, SUMMARY)).toEqual([]);
    expect(
      approvalBlockers({}, { ...NONE, reference_1_verified: true, reference_2_verified: true }, SUMMARY),
    ).toEqual([]);
  });
});

describe("labels", () => {
  it("names the kinds of work and falls back to the code", () => {
    expect(specialtyLabel("civil_works")).toBe("Civil works");
    expect(specialtyLabel("plumbing")).toBe("plumbing");
    expect(listText(["buildings", "roofing"], specialtyLabel)).toBe("Buildings, Roofing");
    expect(listText([])).toBe("–");
  });
});
