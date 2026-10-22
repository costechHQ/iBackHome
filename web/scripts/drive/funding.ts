// Funding a milestone locally without a Stripe account: the driver sends the `checkout.session.completed`
// webhook Stripe would send after the client pays, signed with the local STRIPE_WEBHOOK_SECRET, exactly as the
// backend's own e2e test does (escrow/tests/factories.py). The backend then does everything real: ledger,
// simulated escrow hold, milestone -> funded, audit. The amounts follow the backend's funding rules
// (net = NGN amount / rate, rounded up; paid = net + fee).
import { createHmac, randomUUID } from "node:crypto";

import { API, DriveError, localEnv } from "./env";

/** The local stand-in rate, NGN per 1 unit of the client currency, as Stripe metadata (a decimal string). */
const RATE = "1950.00";

export async function fundMilestone(opts: {
  projectId: string;
  milestoneId: string;
  clientId: string;
  currency: string;
  amountNgnMinor: number;
}): Promise<void> {
  // NGN kobo -> client minor units at RATE (both are 1/100), rounded up, in integers only.
  const rateHundredths = BigInt(RATE.replace(".", ""));
  const net = (BigInt(opts.amountNgnMinor) * 100n + rateHundredths - 1n) / rateHundredths;
  const metadata = {
    purpose: "milestone_funding",
    project_id: opts.projectId,
    milestone_id: opts.milestoneId,
    client_id: opts.clientId,
    currency: opts.currency,
    fx_rate: RATE,
    amount_ngn_minor: String(opts.amountNgnMinor),
    net_minor: String(net),
    fee_minor: "0",
    fee_bps: "0",
  };
  const event = {
    id: `evt_drive_${randomUUID().replace(/-/g, "")}`,
    object: "event",
    type: "checkout.session.completed",
    data: {
      object: {
        id: `cs_drive_${randomUUID().replace(/-/g, "")}`,
        object: "checkout.session",
        mode: "payment",
        payment_status: "paid",
        amount_total: Number(net),
        currency: opts.currency.toLowerCase(),
        client_reference_id: opts.milestoneId,
        metadata,
      },
    },
  };
  const body = JSON.stringify(event);
  const t = Math.floor(Date.now() / 1000);
  const v1 = createHmac("sha256", localEnv("STRIPE_WEBHOOK_SECRET")).update(`${t}.${body}`).digest("hex");
  const res = await fetch(`${API}/api/v1/webhooks/stripe`, {
    method: "POST",
    headers: { "content-type": "application/json", "Stripe-Signature": `t=${t},v1=${v1}` },
    body,
  });
  if (!res.ok) throw new DriveError(`stripe webhook: HTTP ${res.status} ${await res.text()}`);
}
