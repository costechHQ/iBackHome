---
id: WEB-PUBLIC-005
title: "Become a supervisor"
stage: 3
surface: web
role: public
priority: P1
fr: ["FR-02"]
route: "/supervisors"
suggested_target: "web/src/features/public/ (new folder; the Spec lists no public-site feature)"
api: []
links_to: ["WEB-PUBLIC-001", "WEB-PUBLIC-002", "WEB-PUBLIC-003", "WEB-PUBLIC-004", "WEB-PUBLIC-006", "WEB-PUBLIC-007", "WEB-PUBLIC-008", "WEB-PUBLIC-009"]
states: ["default", "desktop", "pub-04b-become-a-supervisor", "loading", "error"]
inventory_refs: ["PUB-04"]
missing_endpoints: []
source_boards: ["SiteMobile.dc.html", "SiteSupervisors.dc.html"]
---

# WEB-PUBLIC-005 · Become a supervisor

## 1. Purpose

Explain supervisor requirements (COREN or NIOB registration, NIN, two guarantors, declared relatives) and send applicants to the Android app.

From the approved board (`SiteSupervisors.dc.html`): "We're looking for registered builders and engineers across Nigeria to visit sites, capture evidence in our app and verify each stage of work. Paid per visit."

From the approved board (`SiteMobile.dc.html`): "Verified supervisors capture site evidence that can't be faked. Your money waits with a licensed escrow partner and is released milestone by milestone — only when the work is confirmed and you approve."

Stage 1 inventory: PUB-04. Priority P1 · FRs FR-02.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1440×3112 | [desktop.png](desktop.png) |
| 2 | PUB-04b · Become a supervisor | mobile | 390×5463 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Site header and footer, Buttons, Escrow trust line, Checklist row, AI-generated label, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Get started", "Apply to be a supervisor", "Start your application".

Navigates to: WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009.

## 5. States and error cases

Designed states: Desktop; PUB-04b · Become a supervisor.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Per-visit rate is PLACEHOLDER until week-one interviews.
- PLACEHOLDER values on this screen (in square brackets on the design): `[₦ RATE]`, `[placeholder until pilot rates are set]`, `[TYPICAL TIME — TO BE CONFIRMED]`, `[REGISTERED COMPANY NAME]`, `[NUMBER]`, `[OFFICE ADDRESS]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
