---
id: WEB-CONTRACTOR-003
title: "Projects dashboard"
stage: 8
surface: web
role: contractor
priority: P0
fr: ["FR-03", "FR-12"]
route: "/c"
suggested_target: "web/src/features/projects/ (contractor views; no contractor feature folder in the Spec)"
api: ["GET /projects", "GET /projects/{id}/milestones"]
links_to: ["WEB-CONTRACTOR-004", "WEB-CONTRACTOR-005", "WEB-CONTRACTOR-006", "WEB-CONTRACTOR-007", "WEB-CONTRACTOR-008", "WEB-CONTRACTOR-009"]
states: ["default", "desktop", "loading", "error"]
inventory_refs: ["CO-01", "CO-02"]
missing_endpoints: ["MX-02", "MX-06"]
source_boards: ["Con-Dashboard.dc.html"]
---

# WEB-CONTRACTOR-003 · Projects dashboard

## 1. Purpose

Contractor projects with what is next on each (BoQ, claim, rework) and money held for them in NGN.

From the approved board (`Con-Dashboard.dc.html`): "Engr. Obi's home on the web portal. Whatever is blocking his next payout comes first. Every amount is in naira, the currency he's paid in. Wed 6 Jan 2027, 17:00 Nigerian time (WAT)."

Stage 1 inventory: CO-01, CO-02. Priority P0 · FRs FR-03, FR-12.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×880 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Contractor top bar, Buttons, Status chip, Escrow trust line, Checklist row, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Project cards | GET /projects -> items[]: id, title, address, status, budget_minor, currency |
| Next action per project | derived from milestones[].status (verified -> approve) |
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "See what to fix", "Revise BoQ".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects`
- `GET /projects/{id}/milestones`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-02: Project invitations
- MX-06: Payout history

Navigates to: WEB-CONTRACTOR-004, WEB-CONTRACTOR-005, WEB-CONTRACTOR-006, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009.

## 5. States and error cases

Designed states: Desktop.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-02: View, accept, decline, resend and cancel an invitation (contractor by client; supplier and ops user by ops). The Spec only says POST /projects "invites contractor".
- MX-06: Contractor and supplier payouts list with references and advice PDFs (payouts table exists; GET /projects/{id}/ledger is client and ops only).
