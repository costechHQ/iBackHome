---
id: WEB-CLIENT-009
title: "Project overview"
stage: 6
surface: web
role: client
priority: P0
fr: ["FR-15", "FR-11", "FR-18"]
route: "/projects/:id"
suggested_target: "web/src/features/dashboard/"
api: ["GET /projects/{id}", "GET /projects/{id}/milestones", "GET /projects/{id}/evidence", "GET /projects/{id}/reports", "GET /projects/{id}/ledger"]
links_to: ["WEB-CLIENT-010", "WEB-CLIENT-011", "WEB-CLIENT-012", "WEB-CLIENT-020"]
states: ["default", "desktop", "the-screen-that-matters-most", "loading", "error"]
inventory_refs: ["CD-01", "CD-04"]
missing_endpoints: ["MX-14", "MX-20", "MX-24"]
source_boards: ["Dash-Overview.dc.html"]
---

# WEB-CLIENT-009 · Project overview

## 1. Purpose

Progress (milestones released), spend vs budget, the milestone stepper, a next-action card, latest evidence, latest report, supervisor, spot checks and escrow balance. Mobile web is the priority.

From the approved board (`Dash-Overview.dc.html`): "One screen that answers: what needs me, how far along is it, where is my money, and can I trust what I'm seeing. Mid-build: two milestones released, Roofing verified and waiting for Chioma."

Stage 1 inventory: CD-01, CD-04. Priority P0 · FRs FR-15, FR-11, FR-18.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×1700 | [desktop.png](desktop.png) |
| 2 | The screen that matters most | mobile | 390×2320 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Project tabs, Client bottom nav, Status chip, Money display, Escrow trust line, Escrow balance card, Spend vs budget bar, Milestone stepper, Evidence card, AI-generated label, Reviewed-by badge, Coming soon placeholder, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Project title | projects.title (GET /projects/{id}) |
| Address | projects.address |
| Project status chip | projects.status |
| Budget | projects.budget_minor + projects.currency |
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |
| Escrow trust line | static copy: "Held by a licensed escrow partner, never by iBackHome." |
| In escrow now | escrow balance: see MX-20 (derive from ledger until an endpoint exists) |
| Report list | GET /projects/{id}/reports -> week_start, status, sent_at |
| Report body | reports.body_md (AI-generated, see MX-13 for one report) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Review and approve", "See the evidence".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}`
- `GET /projects/{id}/milestones`
- `GET /projects/{id}/evidence`
- `GET /projects/{id}/reports`
- `GET /projects/{id}/ledger`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-14: Spot-check history and sharing
- MX-20: Escrow balance per project
- MX-24: Supervisor visits for the client

Navigates to: WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-020.

## 5. States and error cases

Designed states: Desktop; The screen that matters most.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- P2 placeholder only: no form, booking, times or prices. Do not build the feature.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- "Progress vs plan" is shown as milestones released because the Spec has no planned dates (user decision, Stage 2).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-14: Client and ops lists of completed spot checks, and ops "share with client" after closing. The Spec has the supervisor's list, schedule and complete only.
- MX-20: The "in escrow now" figure. escrow_accounts.balance_minor exists but no endpoint returns it; it may be derived from GET /projects/{id}/ledger.
- MX-24: Scheduled visits and the supervisor card (name, body, last visit) on the client dashboard. Partly in GET /projects/{id}; visit history has no endpoint.
