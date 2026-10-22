"use client";

import { zoneLabel } from "@/common/time";
import { Card, CardLabel } from "@/common/ui/surfaces";
import { Time } from "@/common/ui/time";

import type { MilestoneView } from "./use-milestone";

// "Activity · times in GMT" (WEB-CLIENT-013), from the milestone's own dates and its payment in the ledger,
// newest first. People are named by role until the API returns names (MX-26).

export function activityFor({ milestone, money }: Pick<MilestoneView, "milestone" | "money">) {
  const events: { at: string; text: string }[] = [];
  if (milestone.released_at)
    events.push({ at: milestone.released_at, text: "Released: the escrow partner paid the contractor" });
  if (milestone.approved_at) events.push({ at: milestone.approved_at, text: "You approved the release" });
  if (milestone.verified_at) events.push({ at: milestone.verified_at, text: "Verified by the supervisor" });
  if (milestone.claimed_at)
    events.push({ at: milestone.claimed_at, text: `The contractor claimed ${milestone.name} is finished` });
  if (milestone.funded_at)
    events.push({ at: milestone.funded_at, text: "Funded: escrow partner confirmed the hold" });
  if (money.payment) events.push({ at: money.payment.at, text: "You paid by card" });
  // The payment and the hold are written together: keep the payment first when they share a moment.
  return events.sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime());
}

export function ActivityCard({ view, timeZone }: { view: MilestoneView; timeZone: string }) {
  const events = activityFor(view);
  if (!events.length) return null;
  return (
    <Card className="flex flex-col gap-4 p-5">
      <CardLabel>Activity · times in {zoneLabel(events[0]!.at, timeZone)}</CardLabel>
      <ol className="flex flex-col gap-3 border-l border-line pl-4">
        {events.map((e) => (
          <li key={`${e.text}-${e.at}`} className="relative flex flex-col">
            <span aria-hidden className="absolute top-2 -left-5 size-2 rounded-pill bg-navy-900" />
            <span className="type-small text-ink">{e.text}</span>
            <span className="type-caption tracking-normal text-muted">
              <Time iso={e.at} timeZone={timeZone} />
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}
