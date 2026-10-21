---
id: WEB-OPS-008
title: "Supplier verification"
stage: 11
surface: web
role: ops
priority: P1
fr: ["FR-16"]
route: "/ops/suppliers"
suggested_target: "web/src/features/ops-console/"
api: []
links_to: []
states: ["default", "supplier-verification-and-onboarding", "loading", "error"]
inventory_refs: ["OP-15"]
missing_endpoints: ["MX-02", "MX-03", "MX-04"]
source_boards: ["Op-Suppliers.dc.html"]
---

# WEB-OPS-008 · Supplier verification

## 1. Purpose

Invite suppliers and verify them (CAC record, yard visit, payout account, price list) before they can receive orders.

From the approved board (`Op-Suppliers.dc.html`): "Ops invites each supplier, then checks the CAC record, visits the shop, matches the bank account name, and reviews the first price list. Only verified suppliers can receive orders or contribute to the price index."

Stage 1 inventory: OP-15. Priority P1 · FRs FR-16.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Supplier verification and onboarding | desktop | 1440×900 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Search and filters, Status chip, Alert and banner, Quote check result, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Supplier rows | suppliers.name, address, location, verified, paystack_recipient_code (see MX-04) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Invite a supplier", "Approve supplier", "Reject with reason".

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-02: Project invitations
- MX-03: Payout recipient
- MX-04: Supplier business profile and verification

## 5. States and error cases

Designed states: Supplier verification and onboarding.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- Every money movement and sensitive action is audit-logged; the audit log is read-only.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Yard visit step is a design assumption, not in the Spec.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-02: View, accept, decline, resend and cancel an invitation (contractor by client; supplier and ops user by ops). The Spec only says POST /projects "invites contractor".
- MX-03: Look up the account name, save, view and change the payout account for a contractor or supplier (payout_recipients table exists, no endpoint).
- MX-04: Create/update a supplier (name, address, location), ops verification steps and approve/suspend (suppliers table exists, no endpoint).
