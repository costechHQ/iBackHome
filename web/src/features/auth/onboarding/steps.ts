// What a client or contractor still has to do before using their portal (W5b), as one rule the portal layouts,
// /welcome and the tests share. Consent comes first (NDPA 2023); then only what is missing: a name for
// everyone, country and time zone for clients, a payout account for contractors (releases can't be paid
// without one). Everything else can wait for Settings. Ops are staff (their employment terms cover consent)
// and other roles have no web portal, so they never onboard here.

export type Step = "consent" | "details" | "location" | "payout";

type Me = {
  role: string;
  full_name?: string | null;
  country?: string | null;
  consent_required?: boolean;
};

/** The role's steps after consent, in order, as the progress bar shows them. */
export function stepsFor(role: string): Step[] {
  if (role === "client") return ["details", "location"];
  if (role === "contractor") return ["details", "payout"];
  return [];
}

/**
 * Every step still missing, in order. `hasPayout` is null when it couldn't be checked (the payout account
 * route failed): then the contractor isn't held up for it.
 */
export function missingSteps(me: Me, hasPayout: boolean | null = null): Step[] {
  const steps = stepsFor(me.role);
  if (!steps.length) return [];
  const missing: Step[] = [];
  if (me.consent_required) missing.push("consent");
  if (!me.full_name?.trim()) missing.push("details");
  if (steps.includes("location") && !me.country) missing.push("location");
  if (steps.includes("payout") && hasPayout === false) missing.push("payout");
  return missing;
}

export const STEP_LABELS: Record<Exclude<Step, "consent">, string> = {
  details: "Your details",
  location: "Location and time zone",
  payout: "Payout account",
};
