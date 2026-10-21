---
id: WEB-PUBLIC-009
title: "Terms"
stage: 3
surface: web
role: public
priority: P0
fr: []
route: "/terms"
suggested_target: "web/src/features/public/ (new folder; the Spec lists no public-site feature)"
api: []
links_to: ["WEB-PUBLIC-001", "WEB-PUBLIC-002", "WEB-PUBLIC-003", "WEB-PUBLIC-004", "WEB-PUBLIC-005", "WEB-PUBLIC-006", "WEB-PUBLIC-007", "WEB-PUBLIC-008"]
states: ["default", "desktop", "pub-05d-terms", "loading", "error"]
inventory_refs: ["PUB-05"]
missing_endpoints: []
source_boards: ["SiteMobile.dc.html", "SiteTerms.dc.html"]
---

# WEB-PUBLIC-009 · Terms

## 1. Purpose

Terms of use, including that iBackHome never holds client funds.

From the approved board (`SiteTerms.dc.html`): "Last updated [DATE] · For clients, contractors, supervisors and suppliers"

From the approved board (`SiteMobile.dc.html`): "Verified supervisors capture site evidence that can't be faked. Your money waits with a licensed escrow partner and is released milestone by milestone — only when the work is confirmed and you approve."

Stage 1 inventory: PUB-05. Priority P0.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1440×3002 | [desktop.png](desktop.png) |
| 2 | PUB-05d · Terms | mobile | 390×3888 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Site header and footer, Buttons, Escrow trust line, AI-generated label, Reviewed-by badge, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Get started".

Navigates to: WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008.

## 5. States and error cases

Designed states: Desktop; PUB-05d · Terms.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- iBackHome never holds client funds; copy must never say "your money is with iBackHome".
- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Legal text is a PLACEHOLDER structure; final wording needs legal review.
- PLACEHOLDER values on this screen (in square brackets on the design): `[DATE]`, `[AMOUNTS TBC]`, `[NIGERIAN LAW AND COURTS — TO BE CONFIRMED]`, `[LEGAL EMAIL]`, `[REGISTERED COMPANY NAME]`, `[NUMBER]`, `[OFFICE ADDRESS]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
