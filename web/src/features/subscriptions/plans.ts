// The three supervision plans (each with a monthly, bi-annual and annual price) as the public pricing page shows them. The backend is the source of truth for
// what is charged (GET /subscription/plans, and a test there pins these numbers); this copy exists so the
// pricing page renders without a server call. If a price changes, change it in the backend settings and here.
// Clients pay in USD only. Visits are shown, not enforced: the server does not count or cap them yet.

export type PlanCode = "basic" | "standard" | "premium";
export type BillingPeriod = "monthly" | "biannual" | "annual";

/** What one invoice costs for a billing period. Bi-annual pays 5 of 6 months, annual pays 10 of 12. */
export type PeriodPrice = {
  period: BillingPeriod;
  months: number;
  paid_months: number;
  /** Charged each billing period, in US cents. */
  amount_minor: number;
  /** The same months at the monthly price, before the discount. */
  list_amount_minor: number;
  /** amount_minor spread over the months, rounded down. */
  monthly_equivalent_minor: number;
};

export const BILLING_PERIODS: readonly BillingPeriod[] = ["monthly", "biannual", "annual"];

const PERIOD_MONTHS: Record<BillingPeriod, readonly [months: number, paid: number]> = {
  monthly: [1, 1],
  biannual: [6, 5],
  annual: [12, 10],
};

/** Mirrors the server's pricing (a backend test pins the same numbers). Whole-number maths only. */
export function periodPrices(monthlyMinor: number): PeriodPrice[] {
  return BILLING_PERIODS.map((period) => {
    const [months, paid] = PERIOD_MONTHS[period];
    const amount = monthlyMinor * paid;
    return {
      period,
      months,
      paid_months: paid,
      amount_minor: amount,
      list_amount_minor: monthlyMinor * months,
      monthly_equivalent_minor: Math.floor(amount / months),
    };
  });
}

/** The price for one period; falls back to the monthly price if the server sent no periods. */
export function priceFor(plan: PlanView, period: BillingPeriod): PeriodPrice {
  return (
    plan.periods?.find((p) => p.period === period) ??
    periodPrices(plan.amount_minor).find((p) => p.period === period)!
  );
}

export const PERIOD_LABEL: Record<BillingPeriod, string> = {
  monthly: "Monthly",
  biannual: "Bi-annual",
  annual: "Annual",
};

/** "1 month free" / "2 months free" / "" for monthly. */
export function freeMonthsLabel(price: PeriodPrice): string {
  const free = price.months - price.paid_months;
  return free === 0 ? "" : `${free} month${free === 1 ? "" : "s"} free`;
}

/** "billed every month" / "billed every 6 months" / "billed every year". */
export function billedLabel(price: PeriodPrice): string {
  return price.months === 1
    ? "billed every month"
    : price.months === 12
      ? "billed every year"
      : `billed every ${price.months} months`;
}

export type PlanView = {
  code: PlanCode;
  name: string;
  visits_per_month: number;
  currency: string;
  /** US cents. */
  amount_minor: number;
  recommended: boolean;
  /** One entry per billing period. Optional only so older server responses still render. */
  periods?: PeriodPrice[];
};

export const PUBLIC_PLANS: readonly PlanView[] = [
  {
    code: "basic",
    name: "Basic",
    visits_per_month: 2,
    currency: "USD",
    amount_minor: 10_000,
    recommended: false,
    periods: periodPrices(10_000),
  },
  {
    code: "standard",
    name: "Standard",
    visits_per_month: 3,
    currency: "USD",
    amount_minor: 15_000,
    recommended: false,
    periods: periodPrices(15_000),
  },
  {
    code: "premium",
    name: "Premium",
    visits_per_month: 4,
    currency: "USD",
    amount_minor: 20_000,
    recommended: true,
    periods: periodPrices(20_000),
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
