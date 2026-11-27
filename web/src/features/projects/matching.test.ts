import { describe, expect, it } from "vitest";

import { ApiError, NetworkError } from "@/common/api/errors";

import {
  describeMatchError,
  EMPTY_BRIEF,
  toBrief,
  validateBrief,
  workTypeLabel,
  type BriefValues,
} from "./matching";

const VALID: BriefValues = {
  state: "Enugu",
  city: "Enugu",
  workType: "buildings",
  timeline: "Within three months",
  notes: "",
};

describe("validateBrief", () => {
  it("accepts a complete brief, notes optional", () => {
    expect(validateBrief(VALID)).toEqual({});
    expect(validateBrief({ ...VALID, notes: "A four-bedroom bungalow." })).toEqual({});
  });

  it("names every missing answer on an empty brief", () => {
    expect(Object.keys(validateBrief(EMPTY_BRIEF))).toEqual(["state", "city", "workType", "timeline"]);
  });

  it("keeps the notes under the limit", () => {
    expect(validateBrief({ ...VALID, notes: "x".repeat(2001) }).notes).toBeTruthy();
    expect(validateBrief({ ...VALID, notes: "x".repeat(2000) }).notes).toBeUndefined();
  });
});

describe("toBrief", () => {
  it("trims, nulls empty notes and never carries a budget (it comes from the project)", () => {
    const brief = toBrief({ ...VALID, city: "  Enugu ", timeline: " Soon ", notes: "   " });
    expect(brief).toEqual({
      state: "Enugu",
      city: "Enugu",
      work_type: "buildings",
      timeline: "Soon",
      notes: null,
    });
    expect(Object.keys(brief).some((k) => k.includes("budget"))).toBe(false);
  });
});

describe("workTypeLabel", () => {
  it("names the kinds of work and falls back to the code", () => {
    expect(workTypeLabel("civil_works")).toBe("Civil works");
    expect(workTypeLabel("plumbing")).toBe("plumbing");
  });
});

describe("describeMatchError", () => {
  const api = (status: number, code: string) => new ApiError(status, code, "backend text");

  it("explains the common refusals in plain words", () => {
    expect(describeMatchError(new NetworkError(new Error("x")))).toContain("offline");
    expect(describeMatchError(api(409, "project_not_draft"))).toContain("moved past set-up");
    expect(describeMatchError(api(409, "contractor_not_available"))).toContain("no longer available");
    expect(describeMatchError(api(422, "contractor_not_on_shortlist"))).toContain("on your shortlist");
    expect(describeMatchError(api(409, "invalid_transition"))).toContain("Reload");
  });

  it("never shows the raw backend message", () => {
    expect(describeMatchError(api(500, "server_error"))).not.toContain("backend text");
    expect(describeMatchError(new Error("boom"))).not.toContain("boom");
  });
});
