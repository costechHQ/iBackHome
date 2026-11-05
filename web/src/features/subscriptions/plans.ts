// The three supervision plans as the public pricing page shows them. The backend is the source of truth for
// what is charged (GET /subscription/plans, and a test there pins these numbers); this copy exists so the
// pricing page renders without a server call. If a price changes, change it in the backend settings and here.
// Clients pay in USD only. Visits are shown, not enforced: the server does not count or cap them yet.

export type PlanCode = "basic" | "standard" | "premium";

export type PlanView = {
  code: PlanCode;
  name: string;
  visits_per_month: number;
  currency: string;
  /** US cents. */
  amount_minor: number;
  recommended: boolean;
};

export const PUBLIC_PLANS: readonly PlanView[] = [
  {
    code: "basic",
    name: "Basic",
    visits_per_month: 2,
    currency: "USD",
    amount_minor: 10_000,
    recommended: false,
  },
  {
    code: "standard",
    name: "Standard",
    visits_per_month: 3,
    currency: "USD",
    amount_minor: 15_000,
    recommended: false,
  },
  {
    code: "premium",
    name: "Premium",
    visits_per_month: 4,
    currency: "USD",
    amount_minor: 20_000,
    recommended: true,
  },
];

/** What each plan is for, in one line. */
export const PLAN_BLURB: Record<PlanCode, string> = {
  basic: "For a small build, or one where you're on site often yourself.",
  standard: "A visit about every ten days.",
  premium: "Our pick: a visit about every week, for a larger or fast-moving build.",
};

/** "2 site visits a month". */
export function visitsLabel(visits: number): string {
  return `${visits} site visits a month`;
}
