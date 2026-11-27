import { describe, expect, it } from "vitest";

import { ApiError, NetworkError } from "@/common/api/errors";

import { describeError, EMPTY_VALUES, toBody, validate, type ContractorValues } from "./contractor-apply";

const VALID: ContractorValues = {
  ...EMPTY_VALUES,
  businessName: "Obi Building Works",
  contactName: "Chinedu Obi",
  phone: "0803 123 4567",
  email: "obi@example.com",
  years: "12",
  projects: "30",
  states: ["Enugu", "Anambra"],
  specialties: ["buildings", "roofing"],
  cac: "RC1234567",
  r1Name: "Emeka Obi",
  r1Phone: "08051234567",
  r2Name: "Ada Nwosu",
  r2Phone: "+2348071234567",
  consent: true,
};

const fields = (v: ContractorValues) => validate(v).map((p) => p.field);

describe("validate", () => {
  it("accepts a complete form, with or without registration numbers", () => {
    expect(validate(VALID)).toEqual([]);
    expect(validate({ ...VALID, cac: "", corbon: "" })).toEqual([]);
  });

  it("lists everything missing on an empty form", () => {
    expect(fields(EMPTY_VALUES)).toEqual([
      "businessName",
      "contactName",
      "phone",
      "email",
      "years",
      "projects",
      "states",
      "specialties",
      "r1Name",
      "r1Phone",
      "r2Name",
      "r2Phone",
      "consent",
    ]);
  });

  it("needs a state and a kind of work", () => {
    expect(fields({ ...VALID, states: [] })).toEqual(["states"]);
    expect(fields({ ...VALID, specialties: [] })).toEqual(["specialties"]);
  });

  it("keeps years and projects whole and in range", () => {
    expect(fields({ ...VALID, years: "0", projects: "0" })).toEqual([]);
    expect(fields({ ...VALID, years: "81" })).toEqual(["years"]);
    expect(fields({ ...VALID, years: "2.5" })).toEqual(["years"]);
    expect(fields({ ...VALID, projects: "10001" })).toEqual(["projects"]);
    expect(fields({ ...VALID, projects: "-1" })).toEqual(["projects"]);
  });

  it("checks a registration number only when one is typed", () => {
    expect(fields({ ...VALID, cac: "RC" })).toEqual(["cac"]);
    expect(fields({ ...VALID, corbon: "ab" })).toEqual(["corbon"]);
    expect(fields({ ...VALID, cac: "", corbon: "" })).toEqual([]);
  });

  it("says which phone number is wrong", () => {
    const messages = validate(EMPTY_VALUES).map((p) => p.message);
    expect(messages).toContain("Enter your phone number");
    expect(messages).toContain("Enter the first reference’s phone number");
    expect(messages).toContain("Enter the second reference’s phone number");
    expect(validate({ ...VALID, r2Phone: "abc" })[0]?.message).toContain("second reference’s phone number");
  });

  it("needs the consent tick", () => {
    expect(fields({ ...VALID, consent: false })).toEqual(["consent"]);
  });
});

describe("toBody", () => {
  it("trims, numbers the counts, nulls empty registration numbers and never carries a NIN", () => {
    const body = toBody({ ...VALID, businessName: "  Obi Building Works ", cac: "  ", corbon: " CB-123 " });
    expect(body.business_name).toBe("Obi Building Works");
    expect(body.years_in_business).toBe(12);
    expect(body.projects_completed).toBe(30);
    expect(body.cac_rc_number).toBeNull();
    expect(body.corbon_number).toBe("CB-123");
    expect(body.states_served).toEqual(["Enugu", "Anambra"]);
    expect(body.specialties).toEqual(["buildings", "roofing"]);
    expect(body.consent).toBe(true);
    expect(Object.keys(body).some((k) => k.toLowerCase().includes("nin"))).toBe(false);
  });

  it("sends the honeypot as typed, so a bot that fills it is caught", () => {
    expect(toBody(VALID).website).toBe("");
    expect(toBody({ ...VALID, website: "http://spam.example" }).website).toBe("http://spam.example");
  });
});

describe("describeError", () => {
  const api = (status: number, code: string, retry: number | null = null) =>
    new ApiError(status, code, "backend text", retry);

  it("says nothing was sent when offline", () => {
    expect(describeError(new NetworkError(new Error("x"))).message).toContain("offline");
  });

  it("tells a duplicate not to apply again", () => {
    expect(describeError(api(409, "application_exists")).message).toContain("already have an application");
  });

  it("points the reference mistakes at their field", () => {
    expect(describeError(api(422, "references_must_differ")).field).toBe("r2Phone");
    expect(describeError(api(422, "reference_is_applicant")).field).toBe("r1Phone");
    expect(describeError(api(422, "invalid_email")).field).toBe("email");
  });

  it("turns Retry-After into minutes", () => {
    expect(describeError(api(429, "rate_limited", 120)).message).toContain("in about 2 minutes");
    expect(describeError(api(429, "rate_limited")).message).toContain("later");
  });

  it("never shows the raw backend message", () => {
    expect(describeError(api(500, "server_error")).message).not.toContain("backend text");
    expect(describeError(api(422, "validation_error")).message).not.toContain("backend text");
    expect(describeError(new Error("boom")).message).not.toContain("boom");
  });
});
