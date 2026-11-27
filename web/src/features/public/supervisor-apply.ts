import { ApiError, NetworkError } from "@/common/api/errors";
import type { components } from "@/common/api/schema";

// The supervisor application form on /supervisors (ADR 0005, slice 1): the values, the checks we make before
// sending (the backend repeats them, and decides), and what to say when the backend refuses. There is no NIN
// field on purpose: ops check the registration number first and ask for the NIN only afterwards.

export type ApplyBody = components["schemas"]["WebApplicationIn"];

export const REGISTRATION_BODIES = [
  { value: "COREN", label: "COREN (engineer)" },
  { value: "NIOB", label: "NIOB (builder)" },
  { value: "CORBON", label: "CORBON (builder)" },
  { value: "other", label: "Another body" },
] as const;

export type RelativeRow = { name: string; phone: string };

export type ApplyValues = {
  fullName: string;
  phone: string;
  email: string;
  state: string;
  city: string;
  registrationBody: "" | ApplyBody["registration_body"];
  registrationNo: string;
  years: string;
  g1Name: string;
  g1Phone: string;
  g2Name: string;
  g2Phone: string;
  relatives: RelativeRow[];
  consent: boolean;
  /** The honeypot. A person never sees it, so it stays empty; a bot that fills it in is ignored. */
  website: string;
};

export const MAX_RELATIVES = 3;

export const EMPTY_VALUES: ApplyValues = {
  fullName: "",
  phone: "",
  email: "",
  state: "",
  city: "",
  registrationBody: "",
  registrationNo: "",
  years: "",
  g1Name: "",
  g1Phone: "",
  g2Name: "",
  g2Phone: "",
  relatives: [],
  consent: false,
  website: "",
};

export type Field =
  | "fullName"
  | "phone"
  | "email"
  | "state"
  | "city"
  | "registrationBody"
  | "registrationNo"
  | "years"
  | "g1Name"
  | "g1Phone"
  | "g2Name"
  | "g2Phone"
  | "relatives"
  | "consent";

export type Problem = { field: Field; message: string };

/** The id of each field's input, so the "Fix 2 things" summary can link to it. */
export const FIELD_IDS: Record<Field, string> = {
  fullName: "apply-full-name",
  phone: "apply-phone",
  email: "apply-email",
  state: "apply-state",
  city: "apply-city",
  registrationBody: "apply-registration-body",
  registrationNo: "apply-registration-no",
  years: "apply-years",
  g1Name: "apply-g1-name",
  g1Phone: "apply-g1-phone",
  g2Name: "apply-g2-name",
  g2Phone: "apply-g2-phone",
  relatives: "apply-relative-0-name",
  consent: "apply-consent",
};

const PHONE_CHARS = /^\+?[0-9()\s-]+$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function phoneProblem(raw: string, whose: string): string | null {
  const value = raw.trim();
  if (!value) return `Enter ${whose}`;
  const digits = value.replace(/\D/g, "");
  if (!PHONE_CHARS.test(value) || digits.length < 7 || digits.length > 15) {
    return `Enter a valid ${whose}, such as 0803 123 4567`;
  }
  return null;
}

/** Relatives with nothing typed are ignored; a half-filled one is a mistake we point out. */
export function filledRelatives(rows: readonly RelativeRow[]): RelativeRow[] {
  return rows
    .map((r) => ({ name: r.name.trim(), phone: r.phone.trim() }))
    .filter((r) => r.name !== "" || r.phone !== "");
}

export function validate(v: ApplyValues): Problem[] {
  const problems: Problem[] = [];
  const add = (field: Field, message: string | null) => {
    if (message) problems.push({ field, message });
  };
  const name = (value: string, what: string) => (value.trim().length < 2 ? `Enter ${what}` : null);

  add("fullName", name(v.fullName, "your full name"));
  add("phone", phoneProblem(v.phone, "your phone number"));
  add("email", EMAIL.test(v.email.trim()) ? null : "Enter a valid email address");
  add("state", v.state ? null : "Choose your state");
  add("city", name(v.city, "your city or town"));
  add("registrationBody", v.registrationBody ? null : "Choose your registration body");
  add("registrationNo", v.registrationNo.trim().length < 3 ? "Enter your registration number" : null);
  const years = Number(v.years);
  add(
    "years",
    v.years.trim() === "" || !Number.isInteger(years) || years < 0 || years > 60
      ? "Enter your years of experience (0 to 60)"
      : null,
  );
  add("g1Name", name(v.g1Name, "the first guarantor’s name"));
  add("g1Phone", phoneProblem(v.g1Phone, "the first guarantor’s phone number"));
  add("g2Name", name(v.g2Name, "the second guarantor’s name"));
  add("g2Phone", phoneProblem(v.g2Phone, "the second guarantor’s phone number"));
  for (const r of filledRelatives(v.relatives)) {
    if (r.name.length < 2 || phoneProblem(r.phone, "a relative’s phone number")) {
      add("relatives", "Give each relative’s name and phone number, or remove the row");
      break;
    }
  }
  add("consent", v.consent ? null : "Agree to be contacted, and for us to contact your guarantors");
  return problems;
}

export function toBody(v: ApplyValues): ApplyBody {
  return {
    full_name: v.fullName.trim(),
    phone: v.phone.trim(),
    email: v.email.trim(),
    state: v.state,
    city: v.city.trim(),
    registration_body: v.registrationBody as ApplyBody["registration_body"],
    registration_no: v.registrationNo.trim(),
    years_experience: Number(v.years),
    guarantor_1_name: v.g1Name.trim(),
    guarantor_1_phone: v.g1Phone.trim(),
    guarantor_2_name: v.g2Name.trim(),
    guarantor_2_phone: v.g2Phone.trim(),
    relatives: filledRelatives(v.relatives),
    consent: true,
    website: v.website,
  };
}

export type SubmitProblem = { message: string; field?: Field };

/** What to tell the person when the backend (or the network) said no. Never shows a raw backend message. */
export function describeError(error: unknown): SubmitProblem {
  if (error instanceof NetworkError) {
    return { message: "You seem to be offline. Check your connection and try again; nothing was sent." };
  }
  if (error instanceof ApiError) {
    if (error.status === 429) {
      const minutes = error.retryAfterSeconds ? Math.ceil(error.retryAfterSeconds / 60) : null;
      return {
        message: `Too many applications from this connection. Try again ${minutes ? `in about ${minutes} minute${minutes === 1 ? "" : "s"}` : "later"}.`,
      };
    }
    switch (error.code) {
      case "application_exists":
        return {
          message:
            "We already have an application for this phone number or email. We’ll be in touch; there is no need to apply again.",
        };
      case "guarantors_must_differ":
        return { message: "Give two different guarantors.", field: "g2Phone" };
      case "guarantor_is_applicant":
        return { message: "A guarantor can’t be you. Give someone else’s number.", field: "g1Phone" };
      case "invalid_phone":
        return { message: "One of the phone numbers isn’t valid. Check them and try again." };
      case "invalid_email":
        return { message: "That email address isn’t valid.", field: "email" };
    }
    if (error.status === 422)
      return { message: "Some answers weren’t accepted. Check the form and try again." };
  }
  return { message: "Something went wrong on our side and nothing was sent. Please try again in a moment." };
}
