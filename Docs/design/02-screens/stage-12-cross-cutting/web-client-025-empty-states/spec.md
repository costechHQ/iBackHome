---
id: WEB-CLIENT-025
title: "Empty states (client)"
stage: 12
surface: web
role: client
priority: P0
fr: ["FR-15"]
route: "(projects, evidence, reports, ledger, orders, notifications)"
suggested_target: "web/src/common/ (empty state component)"
api: []
links_to: []
states: ["default", "client-projects", "client-evidence", "client-reports", "client-ledger", "client-orders", "client-notifications", "loading", "error"]
inventory_refs: ["NS-10"]
missing_endpoints: []
source_boards: ["X-Empty.dc.html"]
---

# WEB-CLIENT-025 · Empty states (client)

## 1. Purpose

Empty states for the client's main lists.

From the approved board (`X-Empty.dc.html`): "One for every main list, across all five roles. Each says why the list is empty and what makes it fill, with a button only when the person can do something about it."

Stage 1 inventory: NS-10. Priority P0 · FRs FR-15.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Client · Projects | tile | 360×280 | [tile.png](tile.png) |
| 2 | Client · Evidence | tile | 360×280 | [tile-02-client-evidence.png](tile-02-client-evidence.png) |
| 3 | Client · Reports | tile | 360×280 | [tile-03-client-reports.png](tile-03-client-reports.png) |
| 4 | Client · Ledger | tile | 360×280 | [tile-04-client-ledger.png](tile-04-client-ledger.png) |
| 5 | Client · Orders | tile | 360×280 | [tile-05-client-orders.png](tile-05-client-orders.png) |
| 6 | Client · Notifications | tile | 360×280 | [tile-06-client-notifications.png](tile-06-client-notifications.png) |

Components (see [components.md](../../../01-design-system/components.md)): Buttons, Status chip, Empty state, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Create a project", "Fund Foundation".

## 5. States and error cases

Designed states: Client · Projects; Client · Evidence; Client · Reports; Client · Ledger; Client · Orders; Client · Notifications.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Role and project membership decide what is visible (Spec, two-layer authorisation).

## 7. Responsive and accessibility notes

- Designed variants: tile (6).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- The board's buttons lack their button style (see PACKAGE-REPORT); build them as secondary buttons.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
