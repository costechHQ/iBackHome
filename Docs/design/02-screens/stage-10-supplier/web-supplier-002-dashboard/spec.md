---
id: WEB-SUPPLIER-002
title: "Supplier dashboard"
stage: 10
surface: web
role: supplier
priority: P1
fr: ["FR-16", "FR-17"]
route: "/s"
suggested_target: "web/src/features/suppliers/"
api: []
links_to: ["WEB-SUPPLIER-003", "WEB-SUPPLIER-005", "WEB-SUPPLIER-006", "WEB-SUPPLIER-007"]
states: ["default", "mon-11-jan-2027-09-00-wat", "mobile-web", "loading", "error"]
inventory_refs: ["SU-01"]
missing_endpoints: ["MX-05", "MX-06"]
source_boards: ["Sp-Dashboard.dc.html"]
---

# WEB-SUPPLIER-002 · Supplier dashboard

## 1. Purpose

Orders to deliver, payments on the way and stale prices, at a glance.

From the approved board (`Sp-Dashboard.dc.html`): "Nnamdi Ugwu's home: what to deliver and by when, money paid and waiting, and stale prices. Amounts are naira only. iBackHome invited and verified the business in Stage 4."

Stage 1 inventory: SU-01. Priority P1 · FRs FR-16, FR-17.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Mon 11 Jan 2027, 09:00 WAT | desktop | 1280×860 | [desktop.png](desktop.png) |
| 2 | Mobile web | mobile | 390×844 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Supplier top bar and mobile nav, Buttons, Status chip, Escrow trust line, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Order status | material_orders.status: requested \| approved \| delivered \| paid \| cancelled |
| Supplier | material_orders.supplier -> suppliers.name |
| Payout rows | payouts.reference, amount_minor, currency (NGN), status: pending \| success \| failed \| reversed, completed_at: see MX-06 |
| Stale flag | observed_on older than 14 days (price_index.stale_check) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "View order", "Update prices".

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-05: Material order reads
- MX-06: Payout history

Navigates to: WEB-SUPPLIER-003, WEB-SUPPLIER-005, WEB-SUPPLIER-006, WEB-SUPPLIER-007.

## 5. States and error cases

Designed states: Mon 11 Jan 2027, 09:00 WAT; Mobile web.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- A supplier is paid directly only after the supervisor confirms the delivery on site.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-05: List a project's orders, read one order, list a supplier's own orders, put payment on hold or cancel. The Spec has create, approve and delivery only.
- MX-06: Contractor and supplier payouts list with references and advice PDFs (payouts table exists; GET /projects/{id}/ledger is client and ops only).
