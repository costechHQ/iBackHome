---
id: AND-CONTRACTOR-004
title: "Orders (Android)"
stage: 8
surface: android
role: contractor
priority: P1
fr: ["FR-16"]
route: "OrdersScreen"
suggested_target: "mobile/lib/features/orders/ (new folder; not in the Spec)"
api: ["POST /projects/{id}/orders"]
links_to: []
states: ["default", "orders-thu-7-jan", "loading", "error"]
inventory_refs: ["CO-10"]
missing_endpoints: ["MX-05"]
source_boards: ["Con-Android.dc.html"]
---

# AND-CONTRACTOR-004 · Orders (Android)

## 1. Purpose

Contractor order statuses on Android.

From the approved board (`Con-Android.dc.html`): "The same app as the supervisor's, with the contractor's role: see projects, claim a milestone on site, take contractor photos, follow orders and alerts. Uses the Stage 2 Android kit: 48dp targets, flat surfaces, in-app camera only. Every contractor photo is labelled as contractor evidence from shutter to gallery."

Stage 1 inventory: CO-10. Priority P1 · FRs FR-16.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Orders · Thu 7 Jan | android | 360×800 | [android.png](android.png) |

Components (see [components.md](../../../01-design-system/components.md)): Contractor app bottom nav, Buttons, Status chip, Escrow trust line, Card.

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

Actions on the design: "Request materials".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /projects/{id}/orders`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-05: Material order reads

## 5. States and error cases

Designed states: Orders · Thu 7 Jan.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Role and project membership decide what is visible (Spec, two-layer authorisation).

## 7. Responsive and accessibility notes

- Designed variants: android (1).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-05: List a project's orders, read one order, list a supplier's own orders, put payment on hold or cancel. The Spec has create, approve and delivery only.
