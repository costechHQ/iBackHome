"use client";

import { CreditCard, Landmark, Lock, LockOpen, ScrollText } from "lucide-react";
import { useMemo, useState } from "react";

import { toUiState } from "@/common/api/errors";
import { shortId, useLedger, useMilestones, type Milestone } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { escrowNow, ledgerCsv, moneyByMilestone, type Payment, type Release } from "@/common/ledger";
import { formatFxRate, formatMoney } from "@/common/money";
import { formatDate, formatTime } from "@/common/time";
import { Button } from "@/common/ui/button";
import { SelectField } from "@/common/ui/field";
import { ESCROW_LINE } from "@/common/ui/money-display";
import { SegmentedControl } from "@/common/ui/segmented";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import type { Tone } from "@/common/status";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

// WEB-CLIENT-017 Ledger: every payment and release of the project, newest first, from GET /projects/{id}/ledger.
// Rows are read from the ledger's own entries (common/ledger.ts); the CSV is the raw entries, made in the browser
// (MX-22). Payouts to bank accounts appear once the ledger has them; references are short ids until the API has
// display references.

type Row = {
  key: string;
  kind: "funding" | "release";
  at: string;
  milestoneId: string | null;
  title: string;
  detail: string;
  ref: string;
  client: { minor: bigint; currency: string } | null;
  ngnMinor: bigint;
  rate: { fxRate: string; currency: string; note: string } | null;
  status: { label: string; tone: Tone };
};

type Filter = "all" | "funding" | "release" | "payout";

function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function LedgerPage({ projectId }: { projectId: string }) {
  const timeZone = useViewerTimeZone();
  const milestones = useMilestones(projectId);
  const ledger = useLedger(projectId);
  const [filter, setFilter] = useState<Filter>("all");
  const [milestoneFilter, setMilestoneFilter] = useState("");

  const list = milestones.data;
  const entries = ledger.data;
  const data = useMemo(() => {
    if (!list || !entries) return null;
    const read = entries.ledger;
    const byMilestone = moneyByMilestone(list, read);
    const paymentOwner = new Map<Payment, Milestone>();
    const releaseOwner = new Map<Release, Milestone>();
    for (const m of list) {
      const money = byMilestone.get(m.id);
      if (money?.payment) paymentOwner.set(money.payment, m);
      if (money?.release) releaseOwner.set(money.release, m);
    }

    const rows: Row[] = [];
    for (const p of read.payments) {
      const m = paymentOwner.get(p);
      rows.push({
        key: `p-${p.ref}`,
        kind: "funding",
        at: p.at,
        milestoneId: m?.id ?? null,
        title: m ? `Funding · ${m.name}` : "Payment",
        detail: p.held
          ? "Card payment, held by the escrow partner"
          : "Card payment, not held: our team is returning it",
        ref: shortId(p.ref),
        client: { minor: p.paidMinor, currency: p.currency },
        ngnMinor: p.ngnMinor,
        rate: p.fxRate ? { fxRate: p.fxRate, currency: p.currency, note: "Recorded at payment" } : null,
        status: !p.held
          ? { label: "Not held", tone: "warn" }
          : m?.status === "released"
            ? { label: "Confirmed", tone: "neutral" }
            : { label: "Held", tone: "info" },
      });
    }
    for (const r of read.releases) {
      const m = releaseOwner.get(r);
      const payment = m ? byMilestone.get(m.id)?.payment : undefined;
      rows.push({
        key: `r-${r.ref}`,
        kind: "release",
        at: r.at,
        milestoneId: m?.id ?? null,
        title: m ? `Release · ${m.name}` : r.payee === "supplier" ? "Release · material order" : "Release",
        detail:
          r.payee === "supplier"
            ? "Delivery confirmed on site by the supervisor"
            : "Approved by you, verified by the supervisor",
        ref: shortId(r.ref),
        client:
          payment && payment.ngnMinor === r.ngnMinor
            ? { minor: payment.netMinor, currency: payment.currency }
            : null,
        ngnMinor: r.ngnMinor,
        rate: payment?.fxRate
          ? { fxRate: payment.fxRate, currency: payment.currency, note: "Rate at funding" }
          : null,
        status: { label: "Released", tone: "ok" },
      });
    }
    rows.sort((a, b) => b.at.localeCompare(a.at));

    const held = read.payments.filter((p) => p.held);
    const currencies = new Set(held.map((p) => p.currency));
    const oneCurrency = currencies.size === 1 ? [...currencies][0]! : null;
    const releasedMilestones = list.filter((m) => m.status === "released");
    const releasedClient = releasedMilestones.map((m) => byMilestone.get(m.id)?.payment);
    return {
      rows,
      escrow: escrowNow(list, read, byMilestone),
      heldNames: list.filter((m) => m.funded_at && m.status !== "released").map((m) => m.name),
      funded: {
        clientMinor: oneCurrency ? held.reduce((s, p) => s + p.paidMinor, 0n) : null,
        currency: oneCurrency,
        ngnMinor: held.reduce((s, p) => s + p.ngnMinor, 0n),
        count: held.length,
      },
      released: {
        ngnMinor: read.releases.reduce((s, r) => s + r.ngnMinor, 0n),
        clientMinor:
          oneCurrency && releasedClient.every(Boolean)
            ? releasedClient.reduce((s, p) => s + (p?.netMinor ?? 0n), 0n)
            : null,
        count: releasedMilestones.length,
      },
    };
  }, [list, entries]);

  if (milestones.isPending || ledger.isPending) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the ledger">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </Loading>
      </div>
    );
  }
  if (!data || !ledger.data) {
    const state = toUiState(milestones.error ?? ledger.error);
    return <ServerErrorContent reference={state.kind === "server" ? state.requestId : null} />;
  }

  const rows = data.rows.filter(
    (r) => (filter === "all" || r.kind === filter) && (!milestoneFilter || r.milestoneId === milestoneFilter),
  );
  const zone = rows[0] ? formatTime(rows[0].at, timeZone).split(" ").pop() : "";
  const csvName = `ibackhome-ledger-${shortId(projectId)}-${new Date().toISOString().slice(0, 10)}.csv`;
  const money = (row: Row) => (row.client ? formatMoney(row.client.minor, row.client.currency) : "—");
  const Icon = (row: Row) =>
    row.kind === "funding" ? CreditCard : row.title.startsWith("Payout") ? Landmark : LockOpen;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 pb-24 sm:px-10">
      <h1 className="sr-only">Ledger</h1>

      <section className="ibh-on-navy flex flex-col gap-4 rounded-card bg-navy-900 p-6 text-white sm:flex-row sm:items-center">
        <span className="flex size-12 flex-none items-center justify-center rounded-control bg-navy-700">
          <Lock aria-hidden strokeWidth={1.75} className="size-6" />
        </span>
        <p className="type-body-lg flex-1 font-semibold">{ESCROW_LINE}</p>
        <div className="flex flex-col sm:items-end">
          <p className="type-caption text-navy-200 uppercase">In escrow now</p>
          <p className="ibh-tabular type-h2 text-white">
            {data.escrow.client
              ? formatMoney(data.escrow.client.amountMinor, data.escrow.client.currency)
              : formatMoney(data.escrow.ngnMinor, "NGN")}
          </p>
          <p className="ibh-tabular type-small text-navy-200">
            {data.escrow.client ? `${formatMoney(data.escrow.ngnMinor, "NGN")} · ` : ""}
            {data.heldNames.join(", ") || "Nothing held"}
          </p>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="flex flex-col gap-1 p-5">
          <p className="type-small text-slate">Funded by you</p>
          <p className="ibh-tabular type-h2 text-ink">
            {data.funded.clientMinor !== null && data.funded.currency
              ? formatMoney(data.funded.clientMinor, data.funded.currency)
              : formatMoney(data.funded.ngnMinor, "NGN")}
          </p>
          <p className="ibh-tabular type-small text-slate">
            {data.funded.clientMinor !== null ? `${formatMoney(data.funded.ngnMinor, "NGN")} · ` : ""}
            {data.funded.count} {data.funded.count === 1 ? "payment" : "payments"}
          </p>
        </Card>
        <Card className="flex flex-col gap-1 p-5">
          <p className="type-small text-slate">Released from escrow</p>
          <p className="ibh-tabular type-h2 text-ink">{formatMoney(data.released.ngnMinor, "NGN")}</p>
          <p className="ibh-tabular type-small text-slate">
            {data.released.clientMinor !== null && data.funded.currency
              ? `${formatMoney(data.released.clientMinor, data.funded.currency)} · `
              : ""}
            {data.released.count} {data.released.count === 1 ? "milestone" : "milestones"}
          </p>
        </Card>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <SegmentedControl
          label="Show"
          value={filter}
          onChange={setFilter}
          segments={[
            { value: "all", label: "All" },
            { value: "funding", label: "Funding" },
            { value: "release", label: "Releases" },
            { value: "payout", label: "Payouts" },
          ]}
        />
        <SelectField
          label="Milestone"
          className="w-full sm:w-56"
          value={milestoneFilter}
          onChange={(e) => setMilestoneFilter(e.target.value)}
        >
          <option value="">All milestones</option>
          {(milestones.data ?? []).map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </SelectField>
        <p className="type-small ml-auto text-slate max-sm:hidden">Times in your time zone ({zone})</p>
        <Button variant="outline" onClick={() => download(csvName, ledgerCsv(ledger.data.entries))}>
          Download CSV
        </Button>
      </div>

      {rows.length === 0 ? (
        <Card>
          <EmptyState icon={ScrollText} title={filter === "payout" ? "No payouts yet" : "Nothing here yet"}>
            Payments, releases and payouts appear here as soon as they happen.
          </EmptyState>
        </Card>
      ) : (
        <>
          <Table caption="Ledger" className="max-sm:hidden">
            <thead>
              <tr>
                <Th>Date</Th>
                <Th>What</Th>
                <Th>Reference</Th>
                <Th numeric>Your currency</Th>
                <Th numeric>NGN</Th>
                <Th>Rate</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const RowIcon = Icon(row);
                return (
                  <Tr key={row.key}>
                    <Td>
                      <span className="flex flex-col">
                        <span>{formatDate(row.at, timeZone)}</span>
                        <span className="type-caption tracking-normal text-muted">
                          {formatTime(row.at, timeZone)}
                        </span>
                      </span>
                    </Td>
                    <Td>
                      <span className="flex items-start gap-3">
                        <span className="flex size-8 flex-none items-center justify-center rounded-control bg-mist">
                          <RowIcon aria-hidden strokeWidth={1.75} className="size-4 text-navy-900" />
                        </span>
                        <span className="flex flex-col">
                          <span className="font-semibold">{row.title}</span>
                          <span className="type-caption tracking-normal text-muted">{row.detail}</span>
                        </span>
                      </span>
                    </Td>
                    <Td className="type-mono">{row.ref}</Td>
                    <Td numeric>{money(row)}</Td>
                    <Td numeric className="font-semibold">
                      {formatMoney(row.ngnMinor, "NGN")}
                    </Td>
                    <Td>
                      {row.rate ? (
                        <span className="flex flex-col">
                          <span className="ibh-tabular">
                            {formatFxRate(row.rate.fxRate, row.rate.currency)}
                          </span>
                          <span className="type-caption tracking-normal text-muted">{row.rate.note}</span>
                        </span>
                      ) : (
                        "—"
                      )}
                    </Td>
                    <Td>
                      <ToneChip label={row.status.label} tone={row.status.tone} size="small" />
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>

          <Card className="overflow-hidden sm:hidden">
            <ul>
              {rows.map((row) => {
                const RowIcon = Icon(row);
                return (
                  <li key={row.key} className="flex gap-3 border-b border-line p-4 last:border-b-0">
                    <span className="flex size-8 flex-none items-center justify-center rounded-control bg-mist">
                      <RowIcon aria-hidden strokeWidth={1.75} className="size-4 text-navy-900" />
                    </span>
                    <div className="flex flex-1 flex-col gap-0.5">
                      <p className="font-semibold text-ink">{row.title}</p>
                      <p className="type-caption tracking-normal text-muted">
                        {formatDate(row.at, timeZone)}, {formatTime(row.at, timeZone)} · {row.ref}
                      </p>
                      {row.rate ? (
                        <p className="ibh-tabular type-caption tracking-normal text-muted">
                          {formatFxRate(row.rate.fxRate, row.rate.currency)}
                        </p>
                      ) : null}
                    </div>
                    <div className="ibh-tabular flex flex-col items-end gap-1">
                      <span className="font-semibold text-ink">{formatMoney(row.ngnMinor, "NGN")}</span>
                      {row.client ? <span className="type-small text-slate">{money(row)}</span> : null}
                      <ToneChip label={row.status.label} tone={row.status.tone} size="small" />
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>
        </>
      )}

      <p className="type-small text-muted">
        Releases and payouts carry no extra fee. The ledger can&apos;t be edited; a correction is a new entry.
      </p>
    </div>
  );
}
