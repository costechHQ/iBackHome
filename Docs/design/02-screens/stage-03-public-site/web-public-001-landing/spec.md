---
id: WEB-PUBLIC-001
title: "Landing page"
stage: 3
surface: web
role: public
priority: P1
fr: []
route: "/"
suggested_target: "web/src/features/public/ (new folder; the Spec lists no public-site feature)"
api: []
links_to: ["WEB-PUBLIC-002", "WEB-PUBLIC-003", "WEB-PUBLIC-004", "WEB-PUBLIC-005", "WEB-PUBLIC-006", "WEB-PUBLIC-007", "WEB-PUBLIC-008", "WEB-PUBLIC-009"]
states: ["default", "desktop", "pub-01-landing", "loading", "error"]
inventory_refs: ["PUB-01"]
missing_endpoints: []
source_boards: ["SiteLanding.dc.html", "SiteMobile.dc.html"]
---

# WEB-PUBLIC-001 · Landing page

## 1. Purpose

Explain the problem and the promise (proof, not promises; money released milestone by milestone through a licensed escrow partner) and get a client to sign up.

From the approved board (`SiteLanding.dc.html`): "Verified supervisors capture site evidence that can't be faked. Your money waits with a licensed escrow partner and is released milestone by milestone — only when the work is confirmed and you approve."

From the approved board (`SiteMobile.dc.html`): "Verified supervisors capture site evidence that can't be faked. Your money waits with a licensed escrow partner and is released milestone by milestone — only when the work is confirmed and you approve."

Stage 1 inventory: PUB-01. Priority P1.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1440×6588 | [desktop.png](desktop.png) |
| 2 | PUB-01 · Landing | mobile | 390×10642 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Site header and footer, Buttons, Status chip, Money display, Escrow trust line, Evidence card, Three-checks list, Geofence map, AI-generated label, Reviewed-by badge, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Get started".

Navigates to: WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009.

## 5. States and error cases

Designed states: Desktop; PUB-01 · Landing.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- iBackHome never holds client funds; copy must never say "your money is with iBackHome".
- Fees, prices and rates on this screen are PLACEHOLDER figures until week-one interviews and the escrow partner confirm them.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Testimonials and pilot numbers are PLACEHOLDER until real pilot data exists.
- PLACEHOLDER values on this screen (in square brackets on the design): `[Site photo — pilot project]`, `[Name]`, `[City]`, `[REGISTERED COMPANY NAME]`, `[NUMBER]`, `[OFFICE ADDRESS]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
