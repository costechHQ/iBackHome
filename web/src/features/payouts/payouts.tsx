"use client";

import { Landmark, Wallet } from "lucide-react";
import { useState } from "react";

import { useProjectsWithMilestones } from "@/common/api/queries";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { type Tone } from "@/common/status";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { PayoutFields, usePayoutForm, usePayoutRecipient } from "./account";
import { namesText, payoutSummary, type PayoutStage } from "./summary";

// WEB-CONTRACTOR-008 Payouts at /c/payouts. NGN only, times in WAT. Built from the milestones of each project
// and the saved payout account. Not shown until payout history exists (MX-06; PACKAGE-REPORT W-39): the
// transfer reference, its own status ("Retrying"), the advice PDF (MX-22), and supplier payments taken out of a
// milestone (orders come with the materials stage).

const WAT = "Africa/Lagos";

const STAGES: Record<PayoutStage, { label: string; tone: Tone; note: string }> = {
  not_funded: { label: "Not funded", tone: "neutral", note: "When your client funds it" },
  held: { label: "Held in escrow", tone: "info", note: "After verification and approval" },
  releasing: { label: "Being released", tone: "info", note: "Approved, on its way to your account" },
  paused: { label: "Paused", tone: "warn", note: "A dispute is open" },
  released: { label: "Released", tone: "ok", note: "Paid to your account" },
};

function Summary({ label, amount, note }: { label: string; amount: bigint; note: string }) {
  return (
    <Card className="flex flex-col gap-1 p-5">
      <p className="type-small text-slate">{label}</p>
      <p className="ibh-tabular type-h1 text-ink">{formatMoney(amount, "NGN")}</p>
      <p className="type-small text-slate">{note}</p>
    </Card>
  );
}

function PayoutAccount() {
  const saved = usePayoutRecipient();
  const [changing, setChanging] = useState(false);
  const form = usePayoutForm(() => setChanging(false));

  if (changing) {
    return (
      <Card className="flex max-w-2xl flex-col gap-4 p-5">
        <h2 className="type-h3 text-ink">
          {saved.recipient ? "Change payout account" : "Add a payout account"}
        </h2>
        <PayoutFields form={form} />
        <div className="flex flex-wrap gap-3">
          <Button loading={form.save.isPending} disabled={!form.canSave} onClick={form.submit}>
            Save payout account
          </Button>
          <Button variant="secondary" onClick={() => setChanging(false)}>
            Cancel
          </Button>
        </div>
      </Card>
    );
  }
  if (saved.isPending) return <Skeleton className="h-14 w-full" />;
  if (saved.recipient === null) {
    return (
      <Alert tone="warn" title="Add a payout account to be paid">
        Released milestones are paid to a Nigerian bank account in your name or your business’s name.{" "}
        <button
          type="button"
          className="font-semibold text-accent underline"
          onClick={() => setChanging(true)}
        >
          Add a payout account
        </button>
      </Alert>
    );
  }
  if (!saved.recipient) {
    return (
      <Alert tone="warn" title="Your payout account couldn’t be loaded">
        Try again in a moment.
      </Alert>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-card bg-mist px-5 py-3">
      <Landmark aria-hidden strokeWidth={1.75} className="size-5 text-ink" />
      <p className="flex-1 text-ink">
        Paid to <span className="font-semibold">{saved.recipient.bank_name}</span>{" "}
        <span className="type-mono">{saved.recipient.account_number_masked}</span> ·{" "}
        {saved.recipient.account_name}
      </p>
      <button type="button" className="font-semibold text-accent underline" onClick={() => setChanging(true)}>
        Change payout account
      </button>
    </div>
  );
}

export function Payouts() {
  const data = useProjectsWithMilestones();

  if (data.isPending) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-10">
        <Loading label="Loading your payouts">
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-64 w-full" />
        </Loading>
      </div>
    );
  }
  if (data.error) return <ServerErrorContent reference={null} onRetry={data.refetch} />;

  const s = payoutSummary(data.items);
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8 sm:px-10">
      <h1 className="type-h1 text-ink">Payouts</h1>
      <div className="grid gap-4 md:grid-cols-3">
        <Summary
          label="Released so far"
          amount={s.received.minor}
          note={
            s.received.count
              ? `${s.received.count} ${s.received.count === 1 ? "milestone" : "milestones"} on ${s.received.projects} ${s.received.projects === 1 ? "project" : "projects"}`
              : "Nothing released yet"
          }
        />
        <Summary
          label="Held for you now"
          amount={s.held.minor}
          note={
            s.held.names.length
              ? `${namesText(s.held.names)} · after verification and approval`
              : "Nothing held"
          }
        />
        <Summary
          label="Not funded yet"
          amount={s.notFunded.minor}
          note={
            s.notFunded.names.length
              ? `${namesText(s.notFunded.names)} · when your client funds it`
              : "Everything is funded"
          }
        />
      </div>

      <PayoutAccount />

      {s.rows.length === 0 ? (
        <Card>
          <EmptyState icon={Wallet} title="No milestones yet">
            Once a client approves your BoQ, each milestone and its payment shows here.
          </EmptyState>
        </Card>
      ) : (
        <>
          <div className="hidden md:block">
            <Table caption="Payments for each milestone">
              <thead>
                <tr>
                  <Th>Released · WAT</Th>
                  <Th>For</Th>
                  <Th numeric>Amount</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {s.rows.map((r) => (
                  <Tr key={r.id}>
                    <Td className="text-slate">{r.releasedAt ? formatDateTime(r.releasedAt, WAT) : "–"}</Td>
                    <Td>
                      <span className="block font-semibold text-ink">{r.milestone}</span>
                      <span className="type-small text-slate">{r.projectTitle}</span>
                    </Td>
                    <Td numeric className="font-semibold text-ink">
                      {formatMoney(r.amountMinor, "NGN")}
                    </Td>
                    <Td>
                      <ToneChip label={STAGES[r.stage].label} tone={STAGES[r.stage].tone} size="small" />
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </div>
          <ul aria-label="Payments for each milestone" className="flex flex-col gap-3 md:hidden">
            {s.rows.map((r) => (
              <li key={r.id}>
                <Card className="flex flex-col gap-2 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-ink">{r.milestone}</p>
                      <p className="type-small text-slate">{r.projectTitle}</p>
                    </div>
                    <p className="ibh-tabular font-semibold text-ink">{formatMoney(r.amountMinor, "NGN")}</p>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <ToneChip label={STAGES[r.stage].label} tone={STAGES[r.stage].tone} size="small" />
                    <span className="type-small text-slate">
                      {r.releasedAt ? `${formatDateTime(r.releasedAt, WAT)} WAT` : STAGES[r.stage].note}
                    </span>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="type-small text-slate">
        Money for each milestone is held by a licensed escrow partner, never by iBackHome. It’s paid to your
        account once the supervisor verifies the work and your client approves it.
      </p>
    </div>
  );
}
