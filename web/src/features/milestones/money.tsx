"use client";

import { mockPayee } from "@/common/api/mocks";
import { useMock } from "@/common/api/mocks/context";
import { formatDate } from "@/common/time";
import { formatFxRate, formatMoney } from "@/common/money";
import { EscrowTrustLine } from "@/common/ui/money-display";
import { Card, CardLabel } from "@/common/ui/surfaces";

import type { MilestoneView } from "./use-milestone";

// The amounts of one milestone as the client sees them: their currency first (what the ledger converted for it),
// then NGN and the rate recorded at funding (WEB-CLIENT-013 "Money").

export function clientAmounts({ milestone, money }: Pick<MilestoneView, "milestone" | "money">) {
  const payment = money.payment;
  return {
    ngnMinor: milestone.amount_minor,
    client: payment ? { amountMinor: payment.netMinor, currency: payment.currency } : null,
    rate: payment?.fxRate ? { fxRate: payment.fxRate, on: payment.at } : null,
  };
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="type-small text-slate">{label}</dt>
      <dd className="ibh-tabular font-semibold text-ink">{children}</dd>
    </div>
  );
}

/** "Pays to" needs the contractor's payout account (MX-03): from the mock where it's on, otherwise hidden. */
function PaysTo({ label }: { label: string }) {
  const mocked = useMock("MX-03");
  if (!mocked) return null;
  const payee = mockPayee();
  return (
    <Row label={label}>
      {payee.name} · {payee.bank} {payee.accountMasked}
    </Row>
  );
}

export function MoneyCard({ view, timeZone }: { view: MilestoneView; timeZone: string }) {
  const { milestone, money } = view;
  const { client, rate } = clientAmounts(view);
  const both = (clientMinor: bigint | null, ngn: number | bigint) =>
    client && clientMinor !== null
      ? `${formatMoney(clientMinor, client.currency)} · ${formatMoney(ngn, "NGN")}`
      : formatMoney(ngn, "NGN");
  const rateRow =
    client && rate ? (
      <Row label="Rate at funding">
        {formatFxRate(rate.fxRate, client.currency)} · {formatDate(rate.on, timeZone)}
      </Row>
    ) : null;

  let body: React.ReactNode;
  switch (milestone.status) {
    case "pending":
      body = (
        <>
          <Row label="Amount in the BoQ">{formatMoney(milestone.amount_minor, "NGN")}</Row>
          <Row label="In escrow">Nothing yet</Row>
        </>
      );
      break;
    case "released":
      body = (
        <>
          <Row label="Released in total">{both(client?.amountMinor ?? null, milestone.amount_minor)}</Row>
          {money.release ? (
            <Row label="To the contractor">
              {formatMoney(money.release.ngnMinor, "NGN")} · {formatDate(money.release.at, timeZone)}
            </Row>
          ) : null}
        </>
      );
      break;
    default:
      body = (
        <>
          <Row label={`${milestone.status === "disputed" ? "Held" : "In escrow"} for ${milestone.name}`}>
            {both(client?.amountMinor ?? null, milestone.amount_minor)}
          </Row>
          {rateRow}
          <PaysTo label={milestone.status === "funded" ? "Pays to" : "Pays to on release"} />
        </>
      );
  }

  return (
    <Card className="flex flex-col gap-4 p-5">
      <CardLabel>Money</CardLabel>
      <dl className="flex flex-col gap-4">{body}</dl>
      <EscrowTrustLine variant="card" />
    </Card>
  );
}
