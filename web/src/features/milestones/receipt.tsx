"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { shortId } from "@/common/api/queries";
import { mockPayee } from "@/common/api/mocks";
import { useMock } from "@/common/api/mocks/context";
import { useViewerTimeZone } from "@/common/layout/online";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { formatFxRate, formatMoney } from "@/common/money";
import { Button } from "@/common/ui/button";
import { EscrowTrustLine } from "@/common/ui/money-display";
import { Card, CardLabel } from "@/common/ui/surfaces";
import { Time } from "@/common/ui/time";

import { MilestoneDetailLoading } from "./detail";
import { clientAmounts } from "./money";
import { useMilestone } from "./use-milestone";

// The release receipt (WEB-CLIENT-014 "Released · receipt"), built from the milestone and the ledger. There is
// no receipt endpoint or PDF (MX-22): "Download receipt (PDF)" prints this page, which the browser can save as a
// PDF. The reference is the release's ledger ref until the API has display references.

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-6 border-b border-line py-3 last:border-b-0">
      <dt className="text-slate">{label}</dt>
      <dd className="ibh-tabular text-right font-semibold text-ink">{children}</dd>
    </div>
  );
}

export function Receipt({ projectId, milestoneId }: { projectId: string; milestoneId: string }) {
  const timeZone = useViewerTimeZone();
  const search = useSearchParams();
  const mx03 = useMock("MX-03");
  const { view, error, loading, missing } = useMilestone(projectId, milestoneId);
  const ready = Boolean(view && view.milestone.status === "released");

  useEffect(() => {
    if (ready && search.get("print") === "1") window.print();
  }, [ready, search]);

  if (loading) return <MilestoneDetailLoading />;
  if (missing || (view && view.milestone.status !== "released")) return <NotFoundContent />;
  if (error || !view) return <ServerErrorContent reference={null} />;

  const { milestone, money, project } = view;
  const { client, rate } = clientAmounts(view);

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 py-6 print:max-w-none print:p-0">
      <div className="flex flex-col gap-1">
        <p className="type-small text-slate">{project.title}</p>
        <h1 className="type-h2 text-ink">{milestone.name} is released</h1>
      </div>
      <Card className="flex flex-col gap-2 p-6 print:border-0 print:shadow-none">
        <CardLabel>Receipt</CardLabel>
        <p className="type-mono text-ink">
          {money.release ? shortId(money.release.ref) : shortId(milestone.id)}
        </p>
        <dl className="mt-2 flex flex-col">
          <Row label="Amount">
            {client ? `${formatMoney(client.amountMinor, client.currency)} · ` : ""}
            {formatMoney(milestone.amount_minor, "NGN")}
          </Row>
          {client && rate ? <Row label="Rate">{formatFxRate(rate.fxRate, client.currency)}</Row> : null}
          {mx03 ? <Row label="Paid to">{mockPayee().name}</Row> : null}
          {milestone.approved_at ? (
            <Row label="Approved">
              <Time iso={milestone.approved_at} timeZone={timeZone} />
            </Row>
          ) : null}
          {milestone.released_at ? (
            <Row label="Released">
              <Time iso={milestone.released_at} timeZone={timeZone} />
            </Row>
          ) : null}
        </dl>
        <EscrowTrustLine className="mt-3" />
      </Card>
      <div className="flex flex-wrap gap-3 print:hidden">
        <Button size="lg" onClick={() => window.print()}>
          Download receipt (PDF)
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link href={`/projects/${projectId}/milestones/${milestoneId}`}>Back to {milestone.name}</Link>
        </Button>
      </div>
    </div>
  );
}
