import { describe, expect, it } from "vitest";

import { ApiError, NetworkError } from "@/common/api/errors";

import {
  describeError,
  EMPTY_VALUES,
  filledRelatives,
  toBody,
  validate,
  type ApplyValues,
} from "./supervisor-apply";

const VALID: ApplyValues = {
  ...EMPTY_VALUES,
  fullName: "Ngozi Eze",
  phone: "0803 123 4567",
  email: "ngozi@example.com",
  state: "Enugu",
  city: "Enugu",
  registrationBody: "COREN",
  registrationNo: "R.98765",
  years: "8",
  g1Name: "Emeka Obi",
  g1Phone: "08051234567",
  g2Name: "Ada Nwosu",
  g2Phone: "+2348071234567",
  consent: true,
};

const fields = (v: ApplyValues) => validate(v).map((p) => p.field);

describe("validate", () => {
  it("accepts a complete form", () => {
    expect(validate(VALID)).toEqual([]);
  });

  it("lists everything missing on an empty form", () => {
    expect(fields(EMPTY_VALUES)).toEqual([
      "fullName",
      "phone",
      "email",
      "state",
      "city",
      "registrationBody",
      "registrationNo",
      "years",
      "g1Name",
      "g1Phone",
      "g2Name",
      "g2Phone",
      "consent",
    ]);
  });

  it("says which phone number is wrong", () => {
    const messages = validate({ ...EMPTY_VALUES }).map((p) => p.message);
    expect(messages).toContain("Enter your phone number");
    expect(messages).toContain("Enter the first guarantor’s phone number");
    expect(messages).toContain("Enter the second guarantor’s phone number");
    expect(validate({ ...VALID, g2Phone: "abc" })[0]?.message).toContain("second guarantor’s phone number");
  });

  it("takes Nigerian local numbers and international ones, and refuses text", () => {
    expect(fields({ ...VALID, phone: "+44 7700 900123" })).toEqual([]);
    expect(fields({ ...VALID, phone: "abc" })).toEqual(["phone"]);
    expect(fields({ ...VALID, phone: "123" })).toEqual(["phone"]);
  });

  it("checks the email shape", () => {
    expect(fields({ ...VALID, email: "ngozi@" })).toEqual(["email"]);
    expect(fields({ ...VALID, email: "ngozi@example" })).toEqual(["email"]);
  });

  it("keeps years between 0 and 60 and whole", () => {
    expect(fields({ ...VALID, years: "0" })).toEqual([]);
    expect(fields({ ...VALID, years: "61" })).toEqual(["years"]);
    expect(fields({ ...VALID, years: "-1" })).toEqual(["years"]);
    expect(fields({ ...VALID, years: "2.5" })).toEqual(["years"]);
  });

  it("needs the consent tick", () => {
    expect(fields({ ...VALID, consent: false })).toEqual(["consent"]);
  });

  it("ignores empty relative rows but flags a half-filled one", () => {
    expect(fields({ ...VALID, relatives: [{ name: "", phone: "" }] })).toEqual([]);
    expect(fields({ ...VALID, relatives: [{ name: "Chidi Eze", phone: "" }] })).toEqual(["relatives"]);
    expect(fields({ ...VALID, relatives: [{ name: "Chidi Eze", phone: "08012345678" }] })).toEqual([]);
  });
});

describe("toBody", () => {
  it("trims, numbers the years, drops empty relatives and never carries a NIN", () => {
    const body = toBody({
      ...VALID,
      fullName: "  Ngozi Eze ",
      relatives: [
        { name: " Chidi Eze ", phone: " 08012345678 " },
        { name: "", phone: "" },
      ],
    });
    expect(body.full_name).toBe("Ngozi Eze");
    expect(body.years_experience).toBe(8);
    expect(body.relatives).toEqual([{ name: "Chidi Eze", phone: "08012345678" }]);
    expect(body.consent).toBe(true);
    expect(Object.keys(body).some((k) => k.toLowerCase().includes("nin"))).toBe(false);
  });

  it("sends the honeypot as typed, so a bot that fills it is caught", () => {
    expect(toBody(VALID).website).toBe("");
    expect(toBody({ ...VALID, website: "http://spam.example" }).website).toBe("http://spam.example");
  });
});

describe("filledRelatives", () => {
  it("keeps only rows with something in them", () => {
    expect(
      filledRelatives([
        { name: " ", phone: "" },
        { name: "A B", phone: "1" },
      ]),
    ).toEqual([{ name: "A B", phone: "1" }]);
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

  it("points the guarantor mistakes at their field", () => {
    expect(describeError(api(422, "guarantors_must_differ")).field).toBe("g2Phone");
    expect(describeError(api(422, "guarantor_is_applicant")).field).toBe("g1Phone");
    expect(describeError(api(422, "invalid_email")).field).toBe("email");
  });

  it("turns Retry-After into minutes", () => {
    expect(describeError(api(429, "rate_limited", 120)).message).toContain("in about 2 minutes");
    expect(describeError(api(429, "rate_limited", 30)).message).toContain("in about 1 minute.");
    expect(describeError(api(429, "rate_limited")).message).toContain("later");
  });

  it("never shows the raw backend message", () => {
    expect(describeError(api(500, "server_error")).message).not.toContain("backend text");
    expect(describeError(api(422, "validation_error")).message).not.toContain("backend text");
    expect(describeError(new Error("boom")).message).not.toContain("boom");
  });
});
