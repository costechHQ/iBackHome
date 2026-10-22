import { CircleCheck, CircleX, Clock, Copy, KeyRound, MapPin, Video } from "lucide-react";

import type { Audience } from "../status";
import { cn } from "./cn";
import { StatusChip } from "./status-chip";

// Evidence card and three-checks list (components.md, Milestones and evidence). Wherever evidence appears it
// shows the same three checks, in the same order, with the same words. The backend returns the outcome, not
// each check (MX-07); the Spec's evidence state machine says what each outcome means:
//   accepted       -> all three passed
//   flagged        -> boundary and signature passed; the near-duplicate (reuse) check is under review
//   rejected       -> one check failed (reject_reason says which; only the capturer and ops see these)
//   pending_checks -> not checked yet

export const CHECKS = [
  { key: "geofence", label: "Inside the site boundary" },
  { key: "signature", label: "Signed on the registered phone" },
  { key: "reuse", label: "Not reused or edited" },
] as const;

type Result = "pass" | "fail" | "review" | "pending";
type Results = Record<(typeof CHECKS)[number]["key"], Result>;

/**
 * Which check a rejection failed, from the backend's reason (features/evidence/checks.py, which stops at the
 * first failure in this order): the file matches the signed hash, the device signature, the clock and upload
 * window, the site boundary, then a readable, unreused file. Checks after the failing one never ran.
 */
function rejectedAt(reason: string): Results {
  const r = reason.toLowerCase();
  if (/does not match the hash/.test(r)) return { geofence: "pending", signature: "pending", reuse: "fail" };
  if (/device|signature|capture details/.test(r))
    return { geofence: "pending", signature: "fail", reuse: "pending" };
  if (/clock|future|hours after/.test(r)) return { geofence: "pending", signature: "pass", reuse: "pending" };
  if (/outside the site/.test(r)) return { geofence: "fail", signature: "pass", reuse: "pending" };
  if (/could not be read|reuse|duplicate/.test(r))
    return { geofence: "pass", signature: "pass", reuse: "fail" };
  return { geofence: "pending", signature: "pending", reuse: "pending" };
}

export function checkResults(status: string, rejectReason?: string | null): Results {
  switch (status) {
    case "accepted":
      return { geofence: "pass", signature: "pass", reuse: "pass" };
    case "flagged":
      return { geofence: "pass", signature: "pass", reuse: "review" };
    case "rejected":
      return rejectedAt(rejectReason ?? "");
    default:
      return { geofence: "pending", signature: "pending", reuse: "pending" };
  }
}

const RESULT = {
  pass: { icon: CircleCheck, text: "passed", tone: "text-ok-fg" },
  fail: { icon: CircleX, text: "failed", tone: "text-bad-fg" },
  review: { icon: Clock, text: "under review by iBackHome", tone: "text-warn-fg" },
  pending: { icon: Clock, text: "not checked yet", tone: "text-muted" },
} as const;

export function ThreeChecksList({
  status,
  rejectReason,
  compact,
  className,
}: {
  status: string;
  rejectReason?: string | null;
  compact?: boolean;
  className?: string;
}) {
  const results = checkResults(status, rejectReason);
  return (
    <ul
      aria-label="Evidence checks"
      className={cn(compact ? "flex flex-wrap gap-x-3 gap-y-1" : "flex flex-col gap-1.5", className)}
    >
      {CHECKS.map((check) => {
        const r = RESULT[results[check.key]];
        const Icon = r.icon;
        return (
          <li key={check.key} className="type-small flex items-center gap-1.5 text-slate">
            <Icon aria-hidden strokeWidth={1.75} className={cn("size-4 flex-none", r.tone)} />
            <span>
              {check.label}
              <span className="sr-only">: {r.text}</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export type EvidenceCardItem = {
  id: string;
  kind: string;
  status: string;
  captured_by_role: string;
  read_url: string;
  reject_reason?: string | null;
};

const CHECK_ICONS = { geofence: MapPin, signature: KeyRound, reuse: Copy } as const;

/** The three checks as small icons (gallery cards), each with its words for screen readers and on hover. */
export function ThreeChecksIcons({ status, rejectReason }: { status: string; rejectReason?: string | null }) {
  const results = checkResults(status, rejectReason);
  return (
    <ul aria-label="Evidence checks" className="flex items-center gap-1">
      {CHECKS.map((check) => {
        const r = RESULT[results[check.key]];
        const Icon = CHECK_ICONS[check.key];
        return (
          <li key={check.key} title={`${check.label}: ${r.text}`}>
            <Icon aria-hidden strokeWidth={1.75} className={cn("size-4", r.tone)} />
            <span className="sr-only">
              {check.label}: {r.text}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * A gallery card (WEB-CLIENT-010): the photo with its status, then the reference, time, who captured it and the
 * three checks. Read URLs are private and expire after 15 minutes, so this is a plain <img> (never next/image,
 * which would fetch and cache it on the server). Contractor uploads say so and never count toward verification.
 */
export function EvidenceCard({
  item,
  audience,
  reference,
  time,
  className,
}: {
  item: EvidenceCardItem;
  audience: Audience;
  reference: string;
  time: React.ReactNode;
  className?: string;
}) {
  const byContractor = item.captured_by_role === "contractor";
  return (
    <figure
      className={cn(
        "flex flex-col overflow-hidden rounded-card border border-line bg-white shadow-card",
        className,
      )}
    >
      <div className="relative aspect-video bg-placeholder">
        {item.kind === "photo" ? (
          // eslint-disable-next-line @next/next/no-img-element -- signed, expiring, private URL (ADR 0003)
          <img
            src={item.read_url}
            alt={`Evidence ${reference}`}
            width={320}
            height={180}
            loading="lazy"
            decoding="async"
            className="size-full object-cover"
          />
        ) : (
          <div className="flex size-full items-center justify-center text-navy-900">
            <Video aria-hidden strokeWidth={1.75} className="size-7" />
            <span className="sr-only">Video {reference}</span>
          </div>
        )}
        <StatusChip
          entity="evidence"
          state={item.status}
          audience={audience}
          size="small"
          className="absolute top-3 left-3"
        />
      </div>
      <figcaption className="flex flex-col gap-1.5 p-4">
        <p className="type-mono text-ink">{reference}</p>
        <p className="type-small text-slate">{time}</p>
        <div className="flex items-center justify-between gap-2">
          <span className="type-caption rounded-tag border border-line-strong px-2 tracking-normal text-ink">
            {byContractor ? "Contractor" : "Supervisor"}
          </span>
          <ThreeChecksIcons status={item.status} rejectReason={item.reject_reason} />
        </div>
        {byContractor ? (
          <p className="type-caption tracking-normal text-muted">
            Uploaded by the contractor. Doesn&apos;t count toward verification.
          </p>
        ) : null}
      </figcaption>
    </figure>
  );
}
