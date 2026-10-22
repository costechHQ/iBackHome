"use client";

import Link from "next/link";

import type { MilestoneAction } from "@/common/actions";
import { formatClock, formatDate, zoneLabel } from "@/common/time";
import { formatMoney } from "@/common/money";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";

import { clientAmounts } from "./money";
import type { MilestoneView } from "./use-milestone";

// The panel under the stepper that says where this milestone is and what happens next (WEB-CLIENT-013, one
// designed panel per state). Approve and dispute appear only on Verified, and only when the viewer may act.
// The Fund button waits for the funding screens (WEB-CLIENT-007/016, a later stage).

function Panel({
  tone,
  eyebrow,
  title,
  children,
  actions,
}: {
  tone: "mist" | "navy" | "bad" | "ok" | "info";
  eyebrow: string;
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <section
      aria-labelledby="state-title"
      className={cn(
        "flex flex-col gap-3 rounded-card p-6",
        tone === "navy" && "ibh-on-navy bg-navy-900 text-white",
        tone === "mist" && "bg-mist",
        tone === "info" && "bg-accent-tint",
        tone === "ok" && "border-l-4 border-ok-fg bg-ok-bg",
        tone === "bad" && "border-l-4 border-bad-fg bg-bad-bg",
      )}
    >
      <p
        className={cn(
          "type-caption uppercase",
          tone === "navy" ? "text-navy-200" : tone === "bad" ? "text-bad-fg" : "text-muted",
        )}
      >
        {eyebrow}
      </p>
      <h2 id="state-title" className={cn("type-h3", tone === "navy" ? "text-white" : "text-ink")}>
        {title}
      </h2>
      <div className={tone === "navy" ? "text-navy-200" : "text-slate"}>{children}</div>
      {/* On phones the decision buttons live in the screen's bottom bar (detail.tsx). */}
      {actions ? <div className="mt-2 flex flex-wrap gap-3 max-sm:hidden">{actions}</div> : null}
    </section>
  );
}

export function StatePanel({
  view,
  actions,
  timeZone,
  base,
  onApprove,
}: {
  view: MilestoneView;
  actions: Set<MilestoneAction>;
  timeZone: string;
  /** /projects/:id/milestones/:milestoneId */
  base: string;
  onApprove: () => void;
}) {
  const { milestone: m } = view;
  const { client } = clientAmounts(view);
  const releasing = client
    ? formatMoney(client.amountMinor, client.currency)
    : formatMoney(m.amount_minor, "NGN");
  switch (m.status) {
    case "pending":
      return (
        <Panel tone="mist" eyebrow="Next step" title={`Fund ${m.name} to let work start`}>
          <p>The contractor can start once the escrow partner holds the money for this milestone.</p>
        </Panel>
      );
    case "funded":
      return (
        <Panel tone="mist" eyebrow="Work can start" title={`${m.name} is funded`}>
          <p>
            The escrow partner is holding the money. When the contractor claims the work is finished, the
            supervisor visits to check it. Any material orders for this stage are paid from this money after
            delivery is confirmed.
          </p>
        </Panel>
      );
    case "claimed":
      return (
        <Panel
          tone="mist"
          eyebrow="Waiting for the supervisor"
          title={`The contractor says ${m.name} is finished`}
        >
          <p>
            The supervisor visits to check it against the checklist. Nothing for you to do yet. We will
            message you on WhatsApp and email when they decide.
          </p>
        </Panel>
      );
    case "verified":
      return (
        <Panel
          tone="navy"
          eyebrow="Needs your approval"
          title={`${m.name} is verified. Approve to release.`}
          actions={
            actions.has("approve") || actions.has("raise_dispute") ? (
              <>
                {actions.has("approve") ? (
                  <>
                    {/* Phones go to the review step (3 taps in all); wider screens confirm in a dialog. */}
                    <Button asChild size="lg" variant="white-on-navy" className="sm:hidden">
                      <Link href={`${base}/approve`}>Approve release</Link>
                    </Button>
                    <Button size="lg" variant="white-on-navy" className="max-sm:hidden" onClick={onApprove}>
                      Approve release
                    </Button>
                  </>
                ) : null}
                {actions.has("raise_dispute") ? (
                  <Button asChild size="lg" variant="outline-on-navy">
                    <Link href={`${base}/dispute`}>Raise a dispute</Link>
                  </Button>
                ) : null}
              </>
            ) : null
          }
        >
          <p>
            The supervisor checked every item on the checklist on site. Approving tells the escrow partner to
            pay the contractor. If something looks wrong, raise a dispute instead and the money stays held.
          </p>
        </Panel>
      );
    case "approved":
      return (
        <Panel tone="info" eyebrow="Approved" title={`Releasing ${releasing}`}>
          <p>
            You approved. We&apos;ve asked the escrow partner to pay {formatMoney(m.amount_minor, "NGN")} to
            the contractor. This usually takes a few minutes. You can close this page.
          </p>
        </Panel>
      );
    case "disputed":
      return (
        <Panel
          tone="bad"
          eyebrow="Release paused"
          title="Under review by iBackHome"
          actions={
            actions.has("view_dispute") ? (
              <Button asChild size="lg" variant="outline">
                <Link href={`${base}/dispute`}>View dispute</Link>
              </Button>
            ) : null
          }
        >
          <p>
            You raised a dispute. The money stays with the escrow partner until our team decides, and they may
            send a supervisor back to site.
          </p>
        </Panel>
      );
    case "released": {
      const zone = m.released_at ? zoneLabel(m.released_at, timeZone) : "";
      return (
        <Panel
          tone="ok"
          eyebrow="Done"
          title={m.released_at ? `Released on ${formatDate(m.released_at, timeZone)}` : "Released"}
          actions={
            actions.has("view_receipt") ? (
              <>
                <Button asChild size="lg" variant="outline">
                  <Link href={`${base}/receipt`}>View receipt</Link>
                </Button>
                <Button asChild size="lg" variant="secondary">
                  <Link href={`${base}/receipt?print=1`}>Download PDF</Link>
                </Button>
              </>
            ) : null
          }
        >
          {m.approved_at && m.released_at ? (
            <p>
              You approved at {formatClock(m.approved_at, timeZone)} {zone} and the escrow partner confirmed
              at {formatClock(m.released_at, timeZone)} {zone}.
            </p>
          ) : null}
        </Panel>
      );
    }
    default:
      return null;
  }
}
