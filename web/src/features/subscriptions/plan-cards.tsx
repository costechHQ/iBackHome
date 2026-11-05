import { Check } from "lucide-react";
import Link from "next/link";

import { formatMoney } from "@/common/money";
import { Button } from "@/common/ui/button";
import { ToneChip } from "@/common/ui/status-chip";

import { PLAN_BLURB, visitsLabel, type PlanCode, type PlanView } from "./plans";

// The three plans as cards. On the public pricing page they only inform; on the subscription page they are
// a radio group (`onSelect`), so the client chooses a plan before going to the payment page.

const INCLUDED = [
  "A vetted, registered supervisor for your site",
  "Unannounced spot checks by someone else",
  "Every photo and video checked before a release",
  "Weekly report, checked by your supervisor",
];

export function PlanCards({
  plans,
  selected,
  onSelect,
  subscribeHref,
}: {
  plans: readonly PlanView[];
  selected?: PlanCode;
  onSelect?: (code: PlanCode) => void;
  /** Public pricing page: shows a Subscribe button on each card that goes here. */
  subscribeHref?: string;
}) {
  const selectable = Boolean(onSelect);
  return (
    <div
      role={selectable ? "radiogroup" : undefined}
      aria-label={selectable ? "Choose a plan" : undefined}
      className="grid gap-4 md:grid-cols-3"
    >
      {plans.map((plan) => {
        const isSelected = selectable && selected === plan.code;
        const body = (
          <>
            <div className="flex items-center justify-between gap-2">
              <h3 className="type-h2 text-ink">{plan.name}</h3>
              {plan.recommended ? <ToneChip label="Recommended" tone="ok" size="small" /> : null}
            </div>
            <p className="ibh-tabular type-h1 text-ink">
              {formatMoney(plan.amount_minor, plan.currency)}
              <span className="type-small font-normal text-slate"> per project, per month</span>
            </p>
            <p className="type-body font-semibold text-ink">{visitsLabel(plan.visits_per_month)}</p>
            <p className="type-small text-slate">{PLAN_BLURB[plan.code]}</p>
            <ul className="flex flex-col gap-2">
              {INCLUDED.map((item) => (
                <li key={item} className="type-small flex items-start gap-2 text-ink">
                  <Check aria-hidden strokeWidth={2} className="mt-0.5 size-4 flex-none text-ok-fg" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </>
        );
        const base = "flex w-full flex-col gap-3 rounded-card border bg-white p-5 text-left shadow-card";
        return selectable ? (
          <button
            key={plan.code}
            type="button"
            role="radio"
            aria-checked={isSelected}
            onClick={() => onSelect?.(plan.code)}
            className={`${base} ${isSelected ? "border-2 border-accent" : "border-line"}`}
          >
            {body}
          </button>
        ) : (
          <article
            key={plan.code}
            className={`${base} ${plan.recommended ? "border-2 border-accent" : "border-line"}`}
          >
            {body}
            {subscribeHref ? (
              <Button asChild block variant={plan.recommended ? "primary" : "outline"} className="mt-auto">
                <Link href={subscribeHref}>Subscribe to {plan.name}</Link>
              </Button>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
