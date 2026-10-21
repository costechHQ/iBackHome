---
id: WEB-CONTRACTOR-008
title: "Payouts"
stage: 8
surface: web
role: contractor
priority: P1
fr: ["FR-14"]
route: "/c/payouts"
suggested_target: "web/src/features/dashboard/ (no payouts feature on web in the Spec)"
api: []
links_to: ["WEB-CONTRACTOR-003", "WEB-CONTRACTOR-007", "WEB-CONTRACTOR-009"]
states: ["default", "desktop", "loading", "error"]
inventory_refs: ["CO-12"]
missing_endpoints: ["MX-03", "MX-06"]
source_boards: ["Con-Payouts.dc.html"]
---

# WEB-CONTRACTOR-008 · Payouts

## 1. Purpose

Payouts received in NGN, money held for the contractor, and the payout account.

From the approved board (`Con-Payouts.dc.html`): "Naira only: what reached his bank, when, and for which milestone, plus what's still held for him and what has to happen first. Wed 6 Jan 2027 (WAT)."

Stage 1 inventory: CO-12. Priority P1 · FRs FR-14.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×920 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Contractor top bar, Status chip, Escrow trust line, Escrow balance card, Ledger row and receipt, Milestone stepper, Table, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Payout rows | payouts.reference, amount_minor, currency (NGN), status: pending \| success \| failed \| reversed, completed_at: see MX-06 |
| Account | payout_recipients.bank_name, account_name, account_number_masked |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-03: Payout recipient
- MX-06: Payout history

Navigates to: WEB-CONTRACTOR-003, WEB-CONTRACTOR-007, WEB-CONTRACTOR-009.

## 5. States and error cases

Designed states: Desktop.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-03: Look up the account name, save, view and change the payout account for a contractor or supplier (payout_recipients table exists, no endpoint).
- MX-06: Contractor and supplier payouts list with references and advice PDFs (payouts table exists; GET /projects/{id}/ledger is client and ops only).
