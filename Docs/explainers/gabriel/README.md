# Gabriel's explainers

What Gabriel built each day of the backend phase (money: ledger, webhooks, funding, releases, payouts, disputes, quote checker), written for teammates, mentors and judges.

| Day | Feature | Explainer | Summary |
| --- | --- | --- | --- |
| 1 | Ledger and escrow interface | [day-01-ledger-and-escrow-interface.md](day-01-ledger-and-escrow-interface.md) | Double-entry ledger the database itself keeps balanced and append-only, plus the `EscrowProvider` interface with a simulated partner. |
| 2 | Webhook safety | [day-02-webhook-safety.md](day-02-webhook-safety.md) | Signature-checked Stripe, Paystack and escrow webhooks, each stored once in `payment_events` so a re-delivery never counts money twice; `escrow_accounts`; the `request_release` stub. |
| 3 | Stripe funding and Paystack | [day-03-stripe-funding-and-paystack.md](day-03-stripe-funding-and-paystack.md) | A client abroad pays a milestone with Stripe Checkout; the signed webhook writes balanced ledger entries (FX rate stored), holds the naira in escrow and marks the milestone funded. Paystack recipients (masked) and idempotent transfers ready for payouts. |
