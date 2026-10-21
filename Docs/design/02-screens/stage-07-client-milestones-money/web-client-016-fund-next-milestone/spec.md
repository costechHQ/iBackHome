---
id: WEB-CLIENT-016
title: "Fund the next milestone"
stage: 7
surface: web
role: client
priority: P0
fr: ["FR-13"]
route: "/projects/:id/fund/:milestoneId"
suggested_target: "web/src/features/dashboard/"
api: ["POST /projects/{id}/funding", "GET /projects/{id}/milestones"]
links_to: ["WEB-CLIENT-020"]
states: ["default", "fund-plastering-mon-14-dec", "loading", "error"]
inventory_refs: ["CS-09"]
missing_endpoints: []
source_boards: ["Ms-Fund.dc.html"]
---

# WEB-CLIENT-016 · Fund the next milestone

## 1. Purpose

Fund the next milestone once the previous one is released.

From the approved board (`Ms-Fund.dc.html`): "The Stage 5 funding pattern, reused as is. The estimate becomes a fixed amount at today's rate, and the Stripe hand-off, "payment received" and "funded" screens follow exactly as in CS-09 and CS-10."

Stage 1 inventory: CS-09. Priority P0 · FRs FR-13.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Fund Plastering · Mon 14 Dec | desktop | 1280×800 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Buttons, Status chip, Money display, Escrow trust line, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |
| Escrow trust line | static copy: "Held by a licensed escrow partner, never by iBackHome." |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Continue to secure payment".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /projects/{id}/funding`
- `GET /projects/{id}/milestones`

Navigates to: WEB-CLIENT-020.

## 5. States and error cases

Designed states: Fund Plastering · Mon 14 Dec.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Fees, prices and rates on this screen are PLACEHOLDER figures until week-one interviews and the escrow partner confirm them.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[X]`, `[£ FEE]`, `[£ TOTAL]`, `[15 minutes]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
