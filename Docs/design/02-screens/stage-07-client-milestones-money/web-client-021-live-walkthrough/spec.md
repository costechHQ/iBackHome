---
id: WEB-CLIENT-021
title: "Live walkthrough (coming soon)"
stage: 7
surface: web
role: client
priority: P2
fr: ["FR-21"]
route: "/projects/:id/walkthrough"
suggested_target: "web/src/features/dashboard/"
api: []
links_to: ["WEB-CLIENT-010", "WEB-CLIENT-018", "WEB-CLIENT-020"]
states: ["default", "desktop", "mobile-web", "loading", "error"]
inventory_refs: ["CD-05"]
missing_endpoints: []
source_boards: ["Walkthrough.dc.html"]
---

# WEB-CLIENT-021 · Live walkthrough (coming soon)

## 1. Purpose

P2 placeholder that tells clients live video walkthroughs are planned and points to evidence and reports.

From the approved board (`Walkthrough.dc.html`): "A P2 placeholder only. It tells clients what's planned and points them to what works today. There's no booking form, no times and no price, so nothing here can be mistaken for a real booking."

Stage 1 inventory: CD-05. Priority P2 · FRs FR-21.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×760 | [desktop.png](desktop.png) |
| 2 | Mobile web | mobile | 390×760 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Client bottom nav, Buttons, Status chip, Coming soon placeholder, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Open the evidence", "Read the latest report".

Navigates to: WEB-CLIENT-010, WEB-CLIENT-018, WEB-CLIENT-020.

## 5. States and error cases

Designed states: Desktop; Mobile web.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- P2 placeholder only: no form, booking, times or prices. Do not build the feature.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
