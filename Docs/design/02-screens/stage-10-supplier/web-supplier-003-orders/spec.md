---
id: WEB-SUPPLIER-003
title: "Incoming orders"
stage: 10
surface: web
role: supplier
priority: P1
fr: ["FR-16"]
route: "/s/orders"
suggested_target: "web/src/features/suppliers/"
api: []
links_to: ["WEB-SUPPLIER-002", "WEB-SUPPLIER-005", "WEB-SUPPLIER-006", "WEB-SUPPLIER-007"]
states: ["default", "incoming-orders", "mobile-web", "loading", "error"]
inventory_refs: ["SU-01"]
missing_endpoints: ["MX-05"]
source_boards: ["Sp-Orders.dc.html"]
---

# WEB-SUPPLIER-003 · Incoming orders

## 1. Purpose

Approved, delivered, paid and cancelled orders for the supplier.

From the approved board (`Sp-Orders.dc.html`): "Orders reach the supplier only after the client approves them. Each one shows the project and milestone it's paid from and where it stands, from new through delivery to payment."

Stage 1 inventory: SU-01. Priority P1 · FRs FR-16.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Incoming orders | desktop | 1280×860 | [desktop.png](desktop.png) |
| 2 | Mobile web | mobile | 390×844 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Supplier top bar and mobile nav, Status chip, Escrow trust line, Table, Card, Avatar (initials).

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

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-05: Material order reads

Navigates to: WEB-SUPPLIER-002, WEB-SUPPLIER-005, WEB-SUPPLIER-006, WEB-SUPPLIER-007.

## 5. States and error cases

Designed states: Incoming orders; Mobile web.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

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
