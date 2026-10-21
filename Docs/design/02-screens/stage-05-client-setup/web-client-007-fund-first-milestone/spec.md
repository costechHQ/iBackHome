---
id: WEB-CLIENT-007
title: "Fund the first milestone"
stage: 5
surface: web
role: client
priority: P0
fr: ["FR-13"]
route: "/projects/:id/fund/:milestoneId"
suggested_target: "web/src/features/dashboard/ (no escrow feature folder on web in the Spec)"
api: ["POST /projects/{id}/funding", "GET /projects/{id}/milestones", "GET /projects/{id}/ledger"]
links_to: ["WEB-CLIENT-020"]
states: ["default", "cs-09-before-you-pay", "hand-off-to-stripe-checkout", "cs-10-payment-received-waiting-for-escrow", "funded-success", "payment-failed-or-cancelled", "before-you-pay", "waiting-for-escrow", "loading", "error"]
inventory_refs: ["CS-09", "CS-10"]
missing_endpoints: ["MX-20"]
source_boards: ["Setup-Funding.dc.html"]
---

# WEB-CLIENT-007 · Fund the first milestone

## 1. Purpose

Summary before paying, hand-off to Stripe Checkout, payment received but waiting for escrow, funded, and failed or cancelled.

From the approved board (`Setup-Funding.dc.html`): "Summary first, every line visible. Payment happens on Stripe's own secure page; we never see card details. Back on iBackHome the milestone shows "payment received" until the escrow partner confirms the hold — only then is it Funded."

Stage 1 inventory: CS-09, CS-10. Priority P0 · FRs FR-13.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | CS-09 · Before you pay | desktop | 1280×800 | [desktop.png](desktop.png) |
| 2 | Hand-off to Stripe Checkout | desktop | 1280×800 | [desktop-02-hand-off-to-stripe-checkout.png](desktop-02-hand-off-to-stripe-checkout.png) |
| 3 | CS-10 · Payment received — waiting for escrow | desktop | 1280×800 | [desktop-03-cs-10-payment-received-waiting-for-e.png](desktop-03-cs-10-payment-received-waiting-for-e.png) |
| 4 | Funded — success | desktop | 1280×800 | [desktop-04-funded-success.png](desktop-04-funded-success.png) |
| 5 | Payment failed or cancelled | desktop | 1280×800 | [desktop-05-payment-failed-or-cancelled.png](desktop-05-payment-failed-or-cancelled.png) |
| 6 | Before you pay | mobile | 390×844 | [mobile.png](mobile.png) |
| 7 | Waiting for escrow | mobile | 390×700 | [mobile-02-waiting-for-escrow.png](mobile-02-waiting-for-escrow.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Buttons, Status chip, Money display, Escrow trust line, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |
| Escrow trust line | static copy: "Held by a licensed escrow partner, never by iBackHome." |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Continue to secure payment", "Go to my project", "View in ledger", "Try again", "Back to the project", "Back to my project".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /projects/{id}/funding`
- `GET /projects/{id}/milestones`
- `GET /projects/{id}/ledger`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-20: Escrow balance per project

Navigates to: WEB-CLIENT-020.

## 5. States and error cases

Designed states: CS-09 · Before you pay; Hand-off to Stripe Checkout; CS-10 · Payment received — waiting for escrow; Funded — success; Payment failed or cancelled; Before you pay; Waiting for escrow.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- iBackHome never holds client funds; copy must never say "your money is with iBackHome".
- Fees, prices and rates on this screen are PLACEHOLDER figures until week-one interviews and the escrow partner confirm them.

## 7. Responsive and accessibility notes

- Designed variants: desktop (5), mobile (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Fee amount is PLACEHOLDER.
- "Funded" only after the escrow partner confirms; the alert after 30 minutes is a design placeholder.
- PLACEHOLDER values on this screen (in square brackets on the design): `[X]`, `[£ FEE]`, `[£ TOTAL]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-20: The "in escrow now" figure. escrow_accounts.balance_minor exists but no endpoint returns it; it may be derived from GET /projects/{id}/ledger.
