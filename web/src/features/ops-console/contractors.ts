// The pure parts of contractor vetting (ADR 0007, phase 1): the checks ops tick and when approval unlocks.
// Mirrors the backend (features/contractors/service.py): approval needs both references, the registration when
// a CAC or CORBON number was given, and a profile summary ops write themselves (at least 20 characters).

export const SUMMARY_MIN = 20;

export const SPECIALTY_LABELS: Record<string, string> = {
  buildings: "Buildings",
  roofing: "Roofing",
  finishing: "Finishing",
  civil_works: "Civil works",
  other: "Other",
};

export function specialtyLabel(code: string): string {
  return SPECIALTY_LABELS[code] ?? code;
}

export function listText(items: readonly string[], map: (item: string) => string = (s) => s): string {
  return items.length ? items.map(map).join(", ") : "–";
}

export type ContractorChecks = {
  registration_verified: boolean;
  reference_1_verified: boolean;
  reference_2_verified: boolean;
};

export const CHECK_LABELS: Record<keyof ContractorChecks, string> = {
  registration_verified: "Registration checked on the register",
  reference_1_verified: "First reference confirmed by phone",
  reference_2_verified: "Second reference confirmed by phone",
};

type Numbers = { cac_rc_number?: string | null; corbon_number?: string | null };

/** A registration is only checked when the applicant gave a CAC or CORBON number. */
export function registrationRequired(app: Numbers): boolean {
  return Boolean(app.cac_rc_number || app.corbon_number);
}

/** The checks still to do, in the order the page shows them. */
export function openChecks(app: Numbers, checks: ContractorChecks): (keyof ContractorChecks)[] {
  const order: (keyof ContractorChecks)[] = [
    "registration_verified",
    "reference_1_verified",
    "reference_2_verified",
  ];
  return order.filter(
    (k) => (k === "registration_verified" ? registrationRequired(app) : true) && !checks[k],
  );
}

export function summaryReady(summary: string): boolean {
  return summary.trim().length >= SUMMARY_MIN;
}

/** What still blocks "Approve", in plain words (empty when ops may approve). */
export function approvalBlockers(app: Numbers, checks: ContractorChecks, summary: string): string[] {
  const blockers = openChecks(app, checks).map((k) => CHECK_LABELS[k]);
  if (!summaryReady(summary)) blockers.push(`A profile summary of at least ${SUMMARY_MIN} characters`);
  return blockers;
}
