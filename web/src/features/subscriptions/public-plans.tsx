"use client";

import { useState } from "react";

import { PeriodToggle } from "./period-toggle";
import { PlanCards } from "./plan-cards";
import { PUBLIC_PLANS, type BillingPeriod } from "./plans";

// The pricing page's plans: the Monthly / Bi-annual / Annual switch first, then the three plans on that period.
// A client component only because it holds the selected period; the plans themselves come from plans.ts.

export function PublicPlans({ subscribeHref }: { subscribeHref: string }) {
  const [period, setPeriod] = useState<BillingPeriod>("monthly");
  return (
    <div className="flex flex-col gap-6">
      <PeriodToggle value={period} onChange={setPeriod} />
      <PlanCards plans={PUBLIC_PLANS} period={period} subscribeHref={subscribeHref} />
    </div>
  );
}
