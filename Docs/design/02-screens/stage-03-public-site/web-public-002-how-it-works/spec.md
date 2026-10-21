---
id: WEB-PUBLIC-002
title: "How it works"
stage: 3
surface: web
role: public
priority: P1
fr: ["FR-08", "FR-10", "FR-14"]
route: "/how-it-works"
suggested_target: "web/src/features/public/ (new folder; the Spec lists no public-site feature)"
api: []
links_to: ["WEB-PUBLIC-001", "WEB-PUBLIC-003", "WEB-PUBLIC-004", "WEB-PUBLIC-005", "WEB-PUBLIC-006", "WEB-PUBLIC-007", "WEB-PUBLIC-008", "WEB-PUBLIC-009"]
states: ["default", "desktop", "pub-02-how-it-works", "loading", "error"]
inventory_refs: ["PUB-02"]
missing_endpoints: []
source_boards: ["SiteHowItWorks.dc.html", "SiteMobile.dc.html"]
---

# WEB-PUBLIC-002 · How it works

## 1. Purpose

Walk a visitor through evidence capture, the three checks, the two-key release and the escrow partner.

From the approved board (`SiteHowItWorks.dc.html`): "Your contractor builds. A vetted supervisor checks. You decide. A licensed escrow partner pays — and only when both the supervisor and you have said yes."

From the approved board (`SiteMobile.dc.html`): "Verified supervisors capture site evidence that can't be faked. Your money waits with a licensed escrow partner and is released milestone by milestone — only when the work is confirmed and you approve."

Stage 1 inventory: PUB-02. Priority P1 · FRs FR-08, FR-10, FR-14.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1440×3357 | [desktop.png](desktop.png) |
| 2 | PUB-02 · How it works | mobile | 390×5548 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Site header and footer, Buttons, Escrow trust line, Checklist row, AI-generated label, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Get started".

Navigates to: WEB-PUBLIC-001, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009.

## 5. States and error cases

Designed states: Desktop; PUB-02 · How it works.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[REGISTERED COMPANY NAME]`, `[NUMBER]`, `[OFFICE ADDRESS]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
