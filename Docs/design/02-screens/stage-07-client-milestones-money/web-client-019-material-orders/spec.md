---
id: WEB-CLIENT-019
title: "Material orders"
stage: 7
surface: web
role: client
priority: P1
fr: ["FR-16", "FR-17"]
route: "/projects/:id/orders"
suggested_target: "web/src/features/suppliers/"
api: ["POST /orders/{id}/approve", "POST /quotes/check", "GET /price-index"]
links_to: ["WEB-CLIENT-005", "WEB-CLIENT-009", "WEB-CLIENT-010", "WEB-CLIENT-011", "WEB-CLIENT-012", "WEB-CLIENT-013", "WEB-CLIENT-017", "WEB-CLIENT-018", "WEB-CLIENT-020"]
states: ["default", "approve-an-order-tue-15-dec", "orders-and-delivery-confirmation-fri-18-dec", "approve-an-order", "delivery-status", "loading", "error"]
inventory_refs: ["CM-07"]
missing_endpoints: ["MX-05"]
source_boards: ["Orders.dc.html"]
---

# WEB-CLIENT-019 · Material orders

## 1. Purpose

Approve a contractor's material order with the quote check, and follow orders through delivery confirmation.

From the approved board (`Orders.dc.html`): "Engr. Obi requests materials from a verified supplier; the client approves each order line by line against the price index. The supplier is paid from the milestone's escrow, directly by Paystack, only after the supervisor confirms the delivery on site with photos and quantities."

Stage 1 inventory: CM-07. Priority P1 · FRs FR-16, FR-17.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Approve an order · Tue 15 Dec | desktop | 1280×1200 | [desktop.png](desktop.png) |
| 2 | Orders and delivery confirmation · Fri 18 Dec | desktop | 1280×1200 | [desktop-02-orders-and-delivery-confirmation-fri.png](desktop-02-orders-and-delivery-confirmation-fri.png) |
| 3 | Approve an order | mobile | 390×1240 | [mobile.png](mobile.png) |
| 4 | Delivery status | mobile | 390×844 | [mobile-02-delivery-status.png](mobile-02-delivery-status.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Project tabs, Client bottom nav, Buttons, Status chip, Alert and banner, Money display, Escrow trust line, Escrow balance card, Ledger row and receipt, Evidence card, Three-checks list, Quote check result, Table, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Order lines | material_orders.items (quantity as decimal string, unit price) |
| Order total | material_orders.total_minor (server-computed) + currency |
| Order status | material_orders.status: requested \| approved \| delivered \| paid \| cancelled |
| Supplier | material_orders.supplier -> suppliers.name |
| Delivery count | deliveries.quantities, deliveries.evidence_ids, confirmed_by, confirmed_at |
| Flagged lines | POST /quotes/check result: item, quantity, unit price, index price, % difference, reason |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Approve order", "Decline with a reason".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /orders/{id}/approve`
- `POST /quotes/check`
- `GET /price-index`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-05: Material order reads

Navigates to: WEB-CLIENT-005, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-013, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-020.

## 5. States and error cases

Designed states: Approve an order · Tue 15 Dec; Orders and delivery confirmation · Fri 18 Dec; Approve an order; Delivery status.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A supplier is paid directly only after the supervisor confirms the delivery on site.
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.

## 7. Responsive and accessibility notes

- Designed variants: desktop (2), mobile (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-05: List a project's orders, read one order, list a supplier's own orders, put payment on hold or cancel. The Spec has create, approve and delivery only.
