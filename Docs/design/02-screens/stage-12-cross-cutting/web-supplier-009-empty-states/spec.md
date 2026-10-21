---
id: WEB-SUPPLIER-009
title: "Empty states (supplier)"
stage: 12
surface: web
role: supplier
priority: P1
fr: ["FR-16"]
route: "(orders, payouts)"
suggested_target: "web/src/common/ (empty state component)"
api: []
links_to: []
states: ["default", "supplier-orders", "supplier-payouts", "loading", "error"]
inventory_refs: ["NS-10"]
missing_endpoints: []
source_boards: ["X-Empty.dc.html"]
---

# WEB-SUPPLIER-009 · Empty states (supplier)

## 1. Purpose

Empty states for the supplier portal.

From the approved board (`X-Empty.dc.html`): "One for every main list, across all five roles. Each says why the list is empty and what makes it fill, with a button only when the person can do something about it."

Stage 1 inventory: NS-10. Priority P1 · FRs FR-16.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Supplier · Orders | tile | 360×280 | [tile.png](tile.png) |
| 2 | Supplier · Payouts | tile | 360×280 | [tile-02-supplier-payouts.png](tile-02-supplier-payouts.png) |

Components (see [components.md](../../../01-design-system/components.md)): Buttons, Status chip, Empty state, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Update prices".

## 5. States and error cases

Designed states: Supplier · Orders; Supplier · Payouts.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Role and project membership decide what is visible (Spec, two-layer authorisation).

## 7. Responsive and accessibility notes

- Designed variants: tile (2).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Buttons lack their button style on the board; build them as secondary buttons.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
