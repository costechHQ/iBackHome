import type { components } from "@/common/api/schema";

import { describeApplyError, emailProblem, nameProblem, phoneProblem } from "./apply-shared";

// The contractor application form on /contractors (ADR 0007, phase 1): the values, the checks we make before
// sending (the backend repeats them, and decides), and what to say when the backend refuses. There is no NIN
// field: ops check the registration and the references first.

export type ContractorBody = components["schemas"]["ContractorApplicationIn"];
export type Specialty = ContractorBody["specialties"][number];

export const SPECIALTIES: readonly { value: Specialty; label: string }[] = [
  { value: "buildings", label: "Buildings" },
  { value: "roofing", label: "Roofing" },
  { value: "finishing", label: "Finishing" },
  { value: "civil_works", label: "Civil works" },
  { value: "other", label: "Other" },
];

export const MAX_STATES = 10;

export type ContractorValues = {
  businessName: string;
  contactName: string;
  phone: string;
  email: string;
  years: string;
  projects: string;
  states: string[];
  specialties: Specialty[];
  cac: string;
  corbon: string;
  r1Name: string;
  r1Phone: string;
  r2Name: string;
  r2Phone: string;
  consent: boolean;
  /** The honeypot. A person never sees it, so it stays empty; a bot that fills it in is ignored. */
  website: string;
};

export const EMPTY_VALUES: ContractorValues = {
  businessName: "",
  contactName: "",
  phone: "",
  email: "",
  years: "",
  projects: "",
  states: [],
  specialties: [],
  cac: "",
  corbon: "",
  r1Name: "",
  r1Phone: "",
  r2Name: "",
  r2Phone: "",
  consent: false,
  website: "",
};

export type Field =
  | "businessName"
  | "contactName"
  | "phone"
  | "email"
  | "years"
  | "projects"
  | "states"
  | "specialties"
  | "cac"
  | "corbon"
  | "r1Name"
  | "r1Phone"
  | "r2Name"
  | "r2Phone"
  | "consent";

export type Problem = { field: Field; message: string };

/** The id of each field's input, so the "Fix 2 things" summary can link to it. */
export const FIELD_IDS: Record<Field, string> = {
  businessName: "apply-business-name",
  contactName: "apply-contact-name",
  phone: "apply-phone",
  email: "apply-email",
  years: "apply-years",
  projects: "apply-projects",
  states: "apply-state-add",
  specialties: "apply-specialty-buildings",
  cac: "apply-cac",
  corbon: "apply-corbon",
  r1Name: "apply-r1-name",
  r1Phone: "apply-r1-phone",
  r2Name: "apply-r2-name",
  r2Phone: "apply-r2-phone",
  consent: "apply-consent",
};

function wholeNumber(raw: string, max: number): boolean {
  const n = Number(raw);
  return raw.trim() !== "" && Number.isInteger(n) && n >= 0 && n <= max;
}

/** A registration number is optional, but if one is typed it needs at least 3 characters. */
function numberProblem(raw: string, what: string): string | null {
  const value = raw.trim();
  return value !== "" && value.length < 3 ? `Check ${what}: it looks too short` : null;
}

export function validate(v: ContractorValues): Problem[] {
  const problems: Problem[] = [];
  const add = (field: Field, message: string | null) => {
    if (message) problems.push({ field, message });
  };
  add("businessName", nameProblem(v.businessName, "your business name"));
  add("contactName", nameProblem(v.contactName, "the contact person’s name"));
  add("phone", phoneProblem(v.phone, "your phone number"));
  add("email", emailProblem(v.email));
  add("years", wholeNumber(v.years, 80) ? null : "Enter your years in business (0 to 80)");
  add("projects", wholeNumber(v.projects, 10_000) ? null : "Enter how many projects you have completed");
  add("states", v.states.length ? null : "Choose at least one state you work in");
  add("specialties", v.specialties.length ? null : "Choose at least one kind of work");
  add("cac", numberProblem(v.cac, "your CAC RC number"));
  add("corbon", numberProblem(v.corbon, "your CORBON number"));
  add("r1Name", nameProblem(v.r1Name, "the first reference’s name"));
  add("r1Phone", phoneProblem(v.r1Phone, "the first reference’s phone number"));
  add("r2Name", nameProblem(v.r2Name, "the second reference’s name"));
  add("r2Phone", phoneProblem(v.r2Phone, "the second reference’s phone number"));
  add("consent", v.consent ? null : "Agree to be contacted, and for us to contact your references");
  return problems;
}

export function toBody(v: ContractorValues): ContractorBody {
  const optional = (value: string) => (value.trim() === "" ? null : value.trim());
  return {
    business_name: v.businessName.trim(),
    contact_name: v.contactName.trim(),
    phone: v.phone.trim(),
    email: v.email.trim(),
    states_served: v.states,
    specialties: v.specialties,
    years_in_business: Number(v.years),
    projects_completed: Number(v.projects),
    cac_rc_number: optional(v.cac),
    corbon_number: optional(v.corbon),
    reference_1_name: v.r1Name.trim(),
    reference_1_phone: v.r1Phone.trim(),
    reference_2_name: v.r2Name.trim(),
    reference_2_phone: v.r2Phone.trim(),
    consent: true,
    website: v.website,
  };
}

export type SubmitProblem = { message: string; field?: Field };

/** What to tell the person when the backend (or the network) said no. Never shows a raw backend message. */
export function describeError(error: unknown): SubmitProblem {
  return describeApplyError<Field>(error, {
    references_must_differ: { message: "Give two different references.", field: "r2Phone" },
    reference_is_applicant: {
      message: "A reference can’t be you. Give someone else’s number.",
      field: "r1Phone",
    },
    invalid_email: { message: "That email address isn’t valid.", field: "email" },
  });
}
