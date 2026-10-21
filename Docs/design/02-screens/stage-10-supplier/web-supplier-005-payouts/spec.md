---
id: WEB-SUPPLIER-005
title: "Payouts history"
stage: 10
surface: web
role: supplier
priority: P1
fr: ["FR-16"]
route: "/s/payouts"
suggested_target: "web/src/features/suppliers/"
api: []
links_to: ["WEB-SUPPLIER-002", "WEB-SUPPLIER-003", "WEB-SUPPLIER-006", "WEB-SUPPLIER-007"]
states: ["default", "desktop", "mobile-web", "loading", "error"]
inventory_refs: ["SU-03"]
missing_endpoints: ["MX-06", "MX-22"]
source_boards: ["Sp-Payouts.dc.html"]
---

# WEB-SUPPLIER-005 · Payouts history

## 1. Purpose

Payouts received in NGN with references and advice PDFs.

From the approved board (`Sp-Payouts.dc.html`): "Every payment to the supplier in naira, with the order, reference and payment advice. Orders that are confirmed but held stay visible as "On hold", so nothing goes missing."

Stage 1 inventory: SU-03. Priority P1 · FRs FR-16.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×760 | [desktop.png](desktop.png) |
| 2 | Mobile web | mobile | 390×844 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Supplier top bar and mobile nav, Status chip, Escrow trust line, Ledger row and receipt, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Payout rows | payouts.reference, amount_minor, currency (NGN), status: pending \| success \| failed \| reversed, completed_at: see MX-06 |
| Account | payout_recipients.bank_name, account_name, account_number_masked |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-06: Payout history
- MX-22: Receipts and exports

Navigates to: WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-006, WEB-SUPPLIER-007.

## 5. States and error cases

Designed states: Desktop; Mobile web.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-06: Contractor and supplier payouts list with references and advice PDFs (payouts table exists; GET /projects/{id}/ledger is client and ops only).
- MX-22: Release receipt PDF, ledger CSV export and audit log export. No endpoints in the Spec.
