"use client";

import { SegmentedControl, type Segment } from "@/common/ui/segmented";

import { BILLING_PERIODS, PERIOD_LABEL, type BillingPeriod } from "./plans";

// The Monthly / Bi-annual / Annual switch above the plan cards, on the pricing page and the subscription page.
// Bi-annual pays 5 months for 6 and annual pays 10 for 12, so the free months are shown beside the label.

const FREE: Record<BillingPeriod, string> = {
  monthly: "",
  biannual: "1 month free",
  annual: "2 months free",
};

const SEGMENTS: readonly Segment<BillingPeriod>[] = BILLING_PERIODS.map((value) => ({
  value,
  label: PERIOD_LABEL[value],
}));

export function PeriodToggle({
  value,
  onChange,
  className,
}: {
  value: BillingPeriod;
  onChange: (value: BillingPeriod) => void;
  className?: string;
}) {
  return (
    <div className={className}>
      <SegmentedControl
        label="Billing period"
        segments={SEGMENTS}
        value={value}
        onChange={onChange}
        variant="soft"
        className="mx-auto max-w-md rounded-full! border border-line bg-mist shadow-card"
      />
      <p className="type-small mt-2 min-h-5 text-center font-semibold text-ok-fg" aria-live="polite">
        {FREE[value]}
      </p>
    </div>
  );
}
