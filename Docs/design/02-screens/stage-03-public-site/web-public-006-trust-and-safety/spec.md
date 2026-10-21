---
id: WEB-PUBLIC-006
title: "Trust and safety"
stage: 3
surface: web
role: public
priority: P1
fr: ["FR-07", "FR-08", "FR-10", "FR-14", "FR-23"]
route: "/trust"
suggested_target: "web/src/features/public/ (new folder; the Spec lists no public-site feature)"
api: []
links_to: ["WEB-PUBLIC-001", "WEB-PUBLIC-002", "WEB-PUBLIC-003", "WEB-PUBLIC-004", "WEB-PUBLIC-005", "WEB-PUBLIC-007", "WEB-PUBLIC-008", "WEB-PUBLIC-009"]
states: ["default", "desktop", "pub-05a-trust-and-safety", "loading", "error"]
inventory_refs: ["PUB-05"]
missing_endpoints: []
source_boards: ["SiteMobile.dc.html", "SiteTrust.dc.html"]
---

# WEB-PUBLIC-006 · Trust and safety

## 1. Purpose

Explain evidence integrity, escrow, vetting, AI limits and data protection, and how to raise a concern.

From the approved board (`SiteTrust.dc.html`): "Trust is the product. Here's exactly who holds your money, how supervisors are vetted, why evidence can't be faked, and how your data is handled under Nigerian law."

From the approved board (`SiteMobile.dc.html`): "Verified supervisors capture site evidence that can't be faked. Your money waits with a licensed escrow partner and is released milestone by milestone — only when the work is confirmed and you approve."

Stage 1 inventory: PUB-05. Priority P1 · FRs FR-07, FR-08, FR-10, FR-14, FR-23.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1440×3874 | [desktop.png](desktop.png) |
| 2 | PUB-05a · Trust and safety | mobile | 390×7130 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Site header and footer, Buttons, Escrow trust line, Three-checks list, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Get started", "Contact our team".

Navigates to: WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009.

## 5. States and error cases

Designed states: Desktop; PUB-05a · Trust and safety.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- iBackHome never holds client funds; copy must never say "your money is with iBackHome".

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[LICENSED ESCROW PARTNER]`, `[REGULATOR]`, `[NUMBER]`, `[DPO NAME]`, `[DPO EMAIL]`, `[TRUST EMAIL]`, `[REGISTERED COMPANY NAME]`, `[OFFICE ADDRESS]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
