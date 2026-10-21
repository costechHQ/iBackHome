---
id: WEB-SUPPLIER-004
title: "Order detail, delivery and payment"
stage: 10
surface: web
role: supplier
priority: P1
fr: ["FR-16"]
route: "/s/orders/:orderId"
suggested_target: "web/src/features/suppliers/"
api: []
links_to: ["WEB-SUPPLIER-002", "WEB-SUPPLIER-003", "WEB-SUPPLIER-005", "WEB-SUPPLIER-006", "WEB-SUPPLIER-007"]
states: ["default", "approved-to-deliver", "delivered-confirmed-and-paid", "on-hold", "loading", "error"]
inventory_refs: ["SU-02", "SU-03"]
missing_endpoints: ["MX-05", "MX-06"]
source_boards: ["Sp-OrderDetail.dc.html"]
---

# WEB-SUPPLIER-004 · Order detail, delivery and payment

## 1. Purpose

Items, quantities, site location and contact; the supervisor's count (view only); payment status including on hold.

From the approved board (`Sp-OrderDetail.dc.html`): "The supplier sees the items, quantities and approval, then the supervisor's count (view only) and the payment, which comes directly from the milestone escrow once the delivery is confirmed. A confirmed delivery can still wait if the milestone is under review."

Stage 1 inventory: SU-02, SU-03. Priority P1 · FRs FR-16.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Approved, to deliver | desktop | 1280×900 | [desktop.png](desktop.png) |
| 2 | Delivered, confirmed and paid | desktop | 1280×900 | [desktop-02-delivered-confirmed-and-paid.png](desktop-02-delivered-confirmed-and-paid.png) |
| 3 | On hold | mobile | 390×844 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Supplier top bar and mobile nav, Buttons, Status chip, Alert and banner, Escrow trust line, Ledger row and receipt, Evidence card, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Order lines | material_orders.items (quantity as decimal string, unit price) |
| Order total | material_orders.total_minor (server-computed) + currency |
| Order status | material_orders.status: requested \| approved \| delivered \| paid \| cancelled |
| Supplier | material_orders.supplier -> suppliers.name |
| Delivery count | deliveries.quantities, deliveries.evidence_ids, confirmed_by, confirmed_at |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Call site contact".

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-05: Material order reads
- MX-06: Payout history

Navigates to: WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-005, WEB-SUPPLIER-006, WEB-SUPPLIER-007.

## 5. States and error cases

Designed states: Approved, to deliver; Delivered, confirmed and paid; On hold.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A supplier is paid directly only after the supervisor confirms the delivery on site.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.

## 7. Responsive and accessibility notes

- Designed variants: desktop (2), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- INCONSISTENT: "on hold" is not an order status in the Spec (requested, approved, delivered, paid, cancelled). It is shown while the milestone is under review; the backend needs a way to expose it.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-05: List a project's orders, read one order, list a supplier's own orders, put payment on hold or cancel. The Spec has create, approve and delivery only.
- MX-06: Contractor and supplier payouts list with references and advice PDFs (payouts table exists; GET /projects/{id}/ledger is client and ops only).
