"use client";

import { Camera, Check } from "lucide-react";
import Link from "next/link";

import { shortId, useEvidence } from "@/common/api/queries";
import { ToneChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";
import { Time } from "@/common/ui/time";

import type { MilestoneView } from "./use-milestone";

// "Evidence checklist" and "Supervisor's verification" (WEB-CLIENT-013). Only the supervisor's own captures fill
// the checklist; contractor uploads are listed for information only. Once the supervisor has verified, the rows
// are their checklist with the photos for each item. Before that, the designed rows are ops checklist templates,
// which the API doesn't serve yet (PACKAGE-REPORT W-10), so the card lists what the supervisor has captured.

function Header({ title, count }: { title: string; count: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
      <h2 className="type-h3 text-ink">{title}</h2>
      <p className="type-small text-slate">{count}</p>
    </div>
  );
}

export function EvidenceChecklist({
  view,
  timeZone,
  projectBase,
}: {
  view: MilestoneView;
  timeZone: string;
  projectBase: string;
}) {
  const { milestone } = view;
  const verification = milestone.latest_verification;
  const supervisor = useEvidence(milestone.project_id, {
    milestone_id: milestone.id,
    captured_by_role: "supervisor",
  });
  const contractor = useEvidence(milestone.project_id, {
    milestone_id: milestone.id,
    captured_by_role: "contractor",
  });
  const contractorCount = contractor.data?.length ?? 0;

  const rows =
    verification?.decision === "verified" ? (
      <>
        <Header
          title="Evidence checklist"
          count={`${verification.checklist.length} of ${verification.checklist.length} accepted`}
        />
        <ul>
          {verification.checklist.map((item) => {
            const ids = item.evidence_ids ?? [];
            return (
              <li
                key={item.item}
                className="flex items-center gap-4 border-b border-line px-5 py-4 last:border-b-0"
              >
                <span className="flex size-7 flex-none items-center justify-center rounded-control bg-navy-900 text-white">
                  <Check aria-hidden strokeWidth={2.5} className="size-4" />
                </span>
                <div className="flex flex-1 flex-col gap-1">
                  <p className="font-semibold text-ink">{item.item}</p>
                  <p className="type-small flex flex-wrap items-center gap-2 text-slate">
                    {ids.map((id) => (
                      <span
                        key={id}
                        className="type-mono rounded-tag border border-line bg-mist px-1.5 text-ink"
                      >
                        {shortId(id)}
                      </span>
                    ))}
                    <span>
                      {ids.length} {ids.length === 1 ? "photo" : "photos"}
                    </span>
                  </p>
                </div>
                <ToneChip label="Accepted" tone="ok" size="small" />
              </li>
            );
          })}
        </ul>
      </>
    ) : (
      <>
        <Header
          title="Evidence checklist"
          count={`${(supervisor.data ?? []).filter((e) => e.status === "accepted").length} captured`}
        />
        {(supervisor.data ?? []).length ? (
          <ul>
            {(supervisor.data ?? []).map((e) => (
              <li
                key={e.id}
                className="flex items-center gap-4 border-b border-line px-5 py-3 last:border-b-0"
              >
                <span className="flex size-7 flex-none items-center justify-center rounded-control border border-dashed border-line-strong text-slate">
                  <Camera aria-hidden strokeWidth={1.75} className="size-4" />
                </span>
                <p className="type-small flex-1 text-ink">
                  <span className="type-mono">{shortId(e.id)}</span> ·{" "}
                  <Time iso={e.captured_at} timeZone={timeZone} />
                </p>
                <ToneChip
                  label={e.status === "accepted" ? "Accepted" : "Checking"}
                  tone={e.status === "accepted" ? "ok" : "neutral"}
                  size="small"
                />
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-5 py-4 text-slate">
            The supervisor hasn&apos;t captured anything for this milestone yet.
          </p>
        )}
      </>
    );

  return (
    <Card className="overflow-hidden">
      {rows}
      {contractorCount ? (
        <p className="type-small border-t border-line bg-mist px-5 py-3 text-slate">
          The contractor uploaded {contractorCount} {contractorCount === 1 ? "photo" : "photos"}. You can see
          them, but uploads by the contractor do not count toward verification.{" "}
          <Link
            className="font-semibold text-accent underline"
            href={`${projectBase}/evidence?by=contractor`}
          >
            See contractor uploads
          </Link>
        </p>
      ) : null}
    </Card>
  );
}

export function VerificationCard({ view, timeZone }: { view: MilestoneView; timeZone: string }) {
  const verification = view.milestone.latest_verification;
  if (!verification || verification.decision !== "verified") return null;
  return (
    <Card className="flex flex-col gap-3 p-5">
      <h2 className="type-h3 text-ink">Supervisor&apos;s verification</h2>
      <p className="font-semibold text-ink">
        The supervisor verified {view.milestone.name} ·{" "}
        <Time iso={verification.created_at} timeZone={timeZone} />
      </p>
      {verification.notes ? (
        <blockquote className="border-l-2 border-line-strong bg-mist px-4 py-3 text-ink">
          “{verification.notes}”
        </blockquote>
      ) : null}
      <p className="type-small text-muted">
        Signed from their registered phone. All required captures passed the three checks: inside the site
        boundary, device signature valid, not reused or edited.
      </p>
    </Card>
  );
}
