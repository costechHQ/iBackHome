import { Lock } from "lucide-react";

import { formatFxRate, formatMoney } from "../money";
import { cn } from "./cn";

// Money display and escrow trust line (components.md, Money). Clients see their currency first, then NGN and
// the rate recorded for that transaction, with its date. Before funding the client amount is an estimate (≈).
// Contractors, suppliers, supervisors and ops see NGN only.

export const ESCROW_LINE = "Held by a licensed escrow partner, never by iBackHome.";

export type MoneyAmounts = {
  /** The NGN amount: always known (milestones and the ledger are in NGN). */
  ngnMinor: number | bigint;
  /** The client-currency amount, when the viewer is the client and it is known. */
  client?: { amountMinor: number | bigint; currency: string; estimate?: boolean } | null;
  /** NGN per 1 unit of the client currency, as the ledger recorded it, and when. */
  rate?: { fxRate: string; on?: string } | null;
};

/** Inline form: "£6,800.00 · ₦13,260,000 · £1 = ₦1,950.00 · Mon 30 Nov". */
export function MoneyInline({ ngnMinor, client, rate, className }: MoneyAmounts & { className?: string }) {
  const parts = [
    client
      ? client.estimate
        ? `≈ ${formatMoney(client.amountMinor, client.currency, { decimals: "whole" })}`
        : formatMoney(client.amountMinor, client.currency)
      : null,
    formatMoney(ngnMinor, "NGN"),
    client && rate ? `${formatFxRate(rate.fxRate, client.currency)}${rate.on ? ` · ${rate.on}` : ""}` : null,
  ].filter(Boolean);
  return <span className={cn("ibh-tabular", className)}>{parts.join(" · ")}</span>;
}

/** Large form (cards and headers): the main figure, then the NGN amount and the rate line. */
export function MoneyLarge({
  ngnMinor,
  client,
  rate,
  rateLabel = "at",
  className,
}: MoneyAmounts & { rateLabel?: string; className?: string }) {
  const main = client
    ? client.estimate
      ? `≈ ${formatMoney(client.amountMinor, client.currency, { decimals: "whole" })}`
      : formatMoney(client.amountMinor, client.currency)
    : formatMoney(ngnMinor, "NGN");
  return (
    <div className={cn("ibh-tabular flex flex-col items-end gap-0.5", className)}>
      <span className="type-h2 text-ink">{main}</span>
      {client ? <span className="text-slate">{formatMoney(ngnMinor, "NGN")}</span> : null}
      {client && rate ? (
        <span className="type-small text-muted">
          {rate.on ? `${rate.on} ` : ""}
          {rateLabel} {formatFxRate(rate.fxRate, client.currency)}
        </span>
      ) : null}
    </div>
  );
}

/** Lock icon + the escrow line: wherever money is shown, held or moved. */
export function EscrowTrustLine({
  variant = "inline",
  className,
}: {
  variant?: "inline" | "card";
  className?: string;
}) {
  return (
    <p
      className={cn(
        "type-small flex items-start gap-2 text-slate",
        variant === "card" && "rounded-control bg-mist px-4 py-3",
        className,
      )}
    >
      <Lock aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none text-navy-900" />
      {ESCROW_LINE}
    </p>
  );
}
