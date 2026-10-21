---
id: AND-SUPERVISOR-017
title: "Empty states (supervisor)"
stage: 12
surface: android
role: supervisor
priority: P0
fr: ["FR-09"]
route: "(projects, sync, spot checks)"
suggested_target: "mobile/lib/core/ (empty state widget)"
api: []
links_to: []
states: ["default", "supervisor-projects", "supervisor-sync", "supervisor-spot-checks", "loading", "error"]
inventory_refs: ["NS-10"]
missing_endpoints: []
source_boards: ["X-Empty.dc.html"]
---

# AND-SUPERVISOR-017 · Empty states (supervisor)

## 1. Purpose

Empty states for the supervisor app.

From the approved board (`X-Empty.dc.html`): "One for every main list, across all five roles. Each says why the list is empty and what makes it fill, with a button only when the person can do something about it."

Stage 1 inventory: NS-10. Priority P0 · FRs FR-09.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Supervisor · Projects | tile | 360×280 | [tile.png](tile.png) |
| 2 | Supervisor · Sync | tile | 360×280 | [tile-02-supervisor-sync.png](tile-02-supervisor-sync.png) |
| 3 | Supervisor · Spot checks | tile | 360×280 | [tile-03-supervisor-spot-checks.png](tile-03-supervisor-spot-checks.png) |

Components (see [components.md](../../../01-design-system/components.md)): Status chip, Empty state, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

## 5. States and error cases

Designed states: Supervisor · Projects; Supervisor · Sync; Supervisor · Spot checks.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Role and project membership decide what is visible (Spec, two-layer authorisation).

## 7. Responsive and accessibility notes

- Designed variants: tile (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
