---
id: WEB-PUBLIC-003
title: "Pricing"
stage: 3
surface: web
role: public
priority: P1
fr: ["FR-21", "FR-22"]
route: "/pricing"
suggested_target: "web/src/features/public/ (new folder; the Spec lists no public-site feature)"
api: []
links_to: ["WEB-PUBLIC-001", "WEB-PUBLIC-002", "WEB-PUBLIC-004", "WEB-PUBLIC-005", "WEB-PUBLIC-006", "WEB-PUBLIC-007", "WEB-PUBLIC-008", "WEB-PUBLIC-009"]
states: ["default", "desktop", "pub-03-pricing", "loading", "error"]
inventory_refs: ["PUB-03"]
missing_endpoints: []
source_boards: ["SiteMobile.dc.html", "SitePricing.dc.html"]
---

# WEB-PUBLIC-003 · Pricing

## 1. Purpose

Show the supervision subscription, escrow release fee and add-ons, with every figure marked as a placeholder until week-one interviews.

From the approved board (`SitePricing.dc.html`): "A monthly fee for supervision, a small fee each time money is released, and optional extras. You pay in GBP, USD or EUR."

From the approved board (`SiteMobile.dc.html`): "Verified supervisors capture site evidence that can't be faked. Your money waits with a licensed escrow partner and is released milestone by milestone — only when the work is confirmed and you approve."

Stage 1 inventory: PUB-03. Priority P1 · FRs FR-21, FR-22.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1440×2949 | [desktop.png](desktop.png) |
| 2 | PUB-03 · Pricing | mobile | 390×4866 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Site header and footer, Buttons, Status chip, Escrow trust line, Coming soon placeholder, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Get started".

Navigates to: WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009.

## 5. States and error cases

Designed states: Desktop; PUB-03 · Pricing.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Fees, prices and rates on this screen are PLACEHOLDER figures until week-one interviews and the escrow partner confirm them.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- P2 placeholder only: no form, booking, times or prices. Do not build the feature.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- All prices are PLACEHOLDER ([bracketed] on the design).
- Add-ons (walkthrough, land verification) are P2 and shown as coming soon.
- PLACEHOLDER values on this screen (in square brackets on the design): `[£ PRICE]`, `[$ PRICE]`, `[€ PRICE]`, `[X]`, `[TO BE CONFIRMED]`, `[HOW THIS IS CHARGED — TBC]`, `[PRICE]`, `[£ FEE]`, `[£ TOTAL]`, `[REGISTERED COMPANY NAME]`, `[NUMBER]`, `[OFFICE ADDRESS]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
