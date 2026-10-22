"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { milestoneActions } from "@/common/actions";
import { ApiError } from "@/common/api/errors";
import { mockDispute } from "@/common/api/mocks";
import { useMock } from "@/common/api/mocks/context";
import { useViewer } from "@/common/auth/viewer";
import { useOnline, useViewerTimeZone } from "@/common/layout/online";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { Button } from "@/common/ui/button";
import { EscrowTrustLine } from "@/common/ui/money-display";
import { StatusChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";
import { Time } from "@/common/ui/time";

import { MilestoneConflict } from "./conflict";
import { MilestoneDetailLoading } from "./detail";
import { clientAmounts } from "./money";
import { useMilestone } from "./use-milestone";
import { useRaiseDispute } from "./writes";

// WEB-CLIENT-015 Raise a dispute (verified milestones only) and, once raised, "Release paused". The backend takes
// one free-text reason; the designed "What's wrong?" choice starts it. The designed evidence picker has no API
// field and is left out (PACKAGE-REPORT W-12). Reading a dispute back needs MX-10: the reason shown is the one
// raised in this session, else the mock where it's on, else none. Resolved outcomes need MX-10 too.

const REASONS = [
  "The work doesn’t match the evidence",
  "Quality problem in the finished work",
  "Checklist work isn’t finished",
  "Something else",
] as const;
const MAX = 1000;

export const DISPUTE_RAISED_KEY = (milestoneId: string) => ["dispute-raised", milestoneId] as const;

function Header({ title, base, chip }: { title: string; base: string; chip?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <Link
        href={base}
        aria-label="Back to the milestone"
        className="flex size-11 items-center justify-center rounded-control"
      >
        <ChevronLeft aria-hidden strokeWidth={1.75} className="size-6 text-ink" />
      </Link>
      <h1 className="type-h3 flex-1 text-ink">{title}</h1>
      {chip}
    </div>
  );
}

export function DisputeScreen({ projectId, milestoneId }: { projectId: string; milestoneId: string }) {
  const router = useRouter();
  const queries = useQueryClient();
  const viewer = useViewer();
  const timeZone = useViewerTimeZone();
  const online = useOnline();
  const mx10 = useMock("MX-10");
  const ids = { reason: useId(), more: useId(), count: useId() };
  const { view, error, loading, missing } = useMilestone(projectId, milestoneId);
  const raise = useRaiseDispute(projectId);
  const [category, setCategory] = useState<(typeof REASONS)[number] | null>(null);
  const [more, setMore] = useState("");
  const [tried, setTried] = useState(false);

  if (loading) return <MilestoneDetailLoading />;
  if (missing) return <NotFoundContent />;
  if (error || !view) return <ServerErrorContent reference={null} />;

  const { milestone, project } = view;
  const base = `/projects/${projectId}/milestones/${milestoneId}`;
  const actions = milestoneActions(milestone, project, viewer, { online: true });
  const { client } = clientAmounts(view);
  const held = `${client ? `${formatMoney(client.amountMinor, client.currency)} · ` : ""}${formatMoney(milestone.amount_minor, "NGN")}`;

  if (milestone.status === "disputed" && actions.has("view_dispute")) {
    const raised = queries.getQueryData<{ reason: string; created_at: string }>(
      DISPUTE_RAISED_KEY(milestoneId),
    );
    const mocked = mx10 ? mockDispute(milestoneId) : null;
    const reason = raised?.reason ?? mocked?.reason ?? null;
    const raisedAt = raised?.created_at ?? null;
    return (
      <div className="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 pt-4 pb-24 sm:py-8">
        <Header
          title={`Dispute about ${milestone.name}`}
          base={base}
          chip={<StatusChip entity="milestone" state="disputed" audience={viewer.role} />}
        />
        <section className="flex flex-col gap-2 rounded-card border-l-4 border-bad-fg bg-bad-bg p-5">
          <p className="type-caption text-bad-fg uppercase">Release paused</p>
          <h2 className="type-h3 text-ink">Under review by iBackHome</h2>
          <p className="text-slate">{held} stays with the escrow partner until we decide.</p>
        </section>
        {reason ? (
          <Card className="flex flex-col gap-2 p-5">
            <h2 className="type-small font-semibold text-muted uppercase">Your reason</h2>
            <p className="text-ink">{reason}</p>
          </Card>
        ) : null}
        <Card className="flex flex-col gap-3 p-5">
          <h2 className="type-small font-semibold text-muted uppercase">What happens now</h2>
          <ol className="flex flex-col gap-3">
            <li>
              <p className="font-semibold text-ink">You raised the dispute</p>
              {raisedAt ? (
                <p className="type-small text-slate">
                  <Time iso={raisedAt} timeZone={timeZone} />
                </p>
              ) : null}
            </li>
            <li>
              <p className="font-semibold text-ink">The contractor is told on WhatsApp</p>
            </li>
            <li>
              <p className="font-semibold text-ink">iBackHome reviews it</p>
              <p className="type-small text-slate">They may send a supervisor back to site.</p>
            </li>
            <li>
              <p className="font-semibold text-ink">Decision: release, or rework</p>
              <p className="type-small text-slate">You&apos;ll hear on WhatsApp and email.</p>
            </li>
          </ol>
        </Card>
        <EscrowTrustLine />
      </div>
    );
  }

  const conflict = raise.error instanceof ApiError && raise.error.status === 409;
  if (conflict || !actions.has("raise_dispute")) {
    return <MilestoneConflict name={milestone.name} status={milestone.status} href={base} />;
  }

  const problem =
    tried && !category
      ? "Choose what's wrong."
      : tried && more.trim().length < 3
        ? "Tell us what's wrong in a few words."
        : null;
  const submit = () => {
    setTried(true);
    if (!category || more.trim().length < 3) return;
    const reason = `${category}: ${more.trim()}`;
    raise.mutate(
      { milestoneId, reason },
      {
        onSuccess: (dispute) => {
          queries.setQueryData(DISPUTE_RAISED_KEY(milestoneId), {
            reason: dispute.reason,
            created_at: dispute.created_at,
          });
          router.replace(`${base}/dispute`);
        },
      },
    );
  };

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 pt-4 pb-40 sm:py-8">
      <Header title={`Dispute ${milestone.name}`} base={base} />
      <form
        className="flex flex-col gap-5"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <fieldset className="flex flex-col gap-2" aria-describedby={problem ? ids.reason : undefined}>
          <legend className="mb-1 font-semibold text-ink">What&apos;s wrong?</legend>
          {REASONS.map((r) => (
            <label
              key={r}
              className="flex min-h-target items-center gap-3 rounded-control border border-line bg-white px-4"
            >
              <input type="radio" name="category" checked={category === r} onChange={() => setCategory(r)} />
              <span className="text-ink">{r}</span>
            </label>
          ))}
        </fieldset>
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.more} className="type-small font-semibold text-ink">
            Tell us more
          </label>
          <textarea
            id={ids.more}
            rows={5}
            maxLength={MAX}
            value={more}
            onChange={(e) => setMore(e.target.value)}
            aria-describedby={ids.count}
            className="type-body-lg rounded-control border border-line-strong bg-white px-3.5 py-3 text-ink"
          />
          <p id={ids.count} className="type-small text-right text-muted">
            {more.length.toLocaleString("en-GB")} / {MAX.toLocaleString("en-GB")}
          </p>
        </div>
        {problem ? (
          <p id={ids.reason} role="alert" className="type-small text-bad-fg">
            {problem}
          </p>
        ) : null}
        {raise.error && !conflict ? (
          <p role="alert" className="text-bad-fg">
            We couldn&apos;t raise the dispute. Nothing changed and the money stays held. Try again.
          </p>
        ) : null}
        <p className="type-small text-slate">
          The release pauses straight away. The contractor is told on WhatsApp.
        </p>
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-white p-4 sm:static sm:border-0 sm:bg-transparent sm:p-0">
          <Button type="submit" size="lg" block disabled={!online} loading={raise.isPending}>
            Raise dispute and pause release
          </Button>
        </div>
      </form>
    </div>
  );
}
