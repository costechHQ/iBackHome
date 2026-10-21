---
id: WEB-CONTRACTOR-007
title: "Material requests"
stage: 8
surface: web
role: contractor
priority: P1
fr: ["FR-16", "FR-17"]
route: "/c/orders"
suggested_target: "web/src/features/suppliers/"
api: ["POST /projects/{id}/orders", "GET /price-index", "POST /quotes/check"]
links_to: ["WEB-CONTRACTOR-003", "WEB-CONTRACTOR-008", "WEB-CONTRACTOR-009"]
states: ["default", "new-request-thu-7-jan", "orders-statuses", "loading", "error"]
inventory_refs: ["CO-09", "CO-10", "CO-11"]
missing_endpoints: ["MX-05"]
source_boards: ["Con-Orders.dc.html"]
---

# WEB-CONTRACTOR-007 · Material requests

## 1. Purpose

Request materials from verified suppliers using index items, and follow order statuses.

From the approved board (`Con-Orders.dc.html`): "The contractor asks a verified supplier for materials, against a funded milestone. While he types, each line shows the Enugu price index, so he knows before sending what the client will see flagged. The server works out the total. The client approves, the supervisor confirms delivery, then the supplier is paid from that milestone's escrow."

Stage 1 inventory: CO-09, CO-10, CO-11. Priority P1 · FRs FR-16, FR-17.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | New request · Thu 7 Jan | desktop | 1280×1140 | [desktop.png](desktop.png) |
| 2 | Orders · statuses | desktop | 1280×760 | [desktop-02-orders-statuses.png](desktop-02-orders-statuses.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Contractor top bar, Buttons, Status chip, Alert and banner, Escrow trust line, Quote check result, Table, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Order lines | material_orders.items (quantity as decimal string, unit price) |
| Order total | material_orders.total_minor (server-computed) + currency |
| Order status | material_orders.status: requested \| approved \| delivered \| paid \| cancelled |
| Supplier | material_orders.supplier -> suppliers.name |
| Delivery count | deliveries.quantities, deliveries.evidence_ids, confirmed_by, confirmed_at |
| Index rows | GET /price-index -> item, unit, price_minor, currency, supplier_name, observed_on, source |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "+ Add item", "Send to Chioma for approval", "Request materials".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /projects/{id}/orders`
- `GET /price-index`
- `POST /quotes/check`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-05: Material order reads

Navigates to: WEB-CONTRACTOR-003, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009.

## 5. States and error cases

Designed states: New request · Thu 7 Jan; Orders · statuses.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A supplier is paid directly only after the supervisor confirms the delivery on site.
- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.

## 7. Responsive and accessibility notes

- Designed variants: desktop (2).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-05: List a project's orders, read one order, list a supplier's own orders, put payment on hold or cancel. The Spec has create, approve and delivery only.
