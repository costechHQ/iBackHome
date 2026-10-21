---
id: WEB-CONTRACTOR-005
title: "Milestones and claim"
stage: 8
surface: web
role: contractor
priority: P0
fr: ["FR-12"]
route: "/c/projects/:id/milestones"
suggested_target: "web/src/features/milestones/"
api: ["GET /projects/{id}/milestones", "POST /milestones/{id}/claim"]
links_to: ["WEB-CONTRACTOR-003", "WEB-CONTRACTOR-004", "WEB-CONTRACTOR-007", "WEB-CONTRACTOR-008", "WEB-CONTRACTOR-009"]
states: ["default", "milestone-list-plastering-ready-to-claim", "claim-confirmation", "claimed-waiting-for-the-supervisor", "loading", "error"]
inventory_refs: ["CO-05"]
missing_endpoints: []
source_boards: ["Con-Milestones.dc.html"]
---

# WEB-CONTRACTOR-005 · Milestones and claim

## 1. Purpose

Milestone list, claim confirmation, and claimed while waiting for the supervisor.

From the approved board (`Con-Milestones.dc.html`): "The contractor sees each milestone with the money in naira: paid to him, paid to suppliers, and waiting in escrow. Only a funded milestone can be claimed. The required checklist is shown up front, because that's exactly what the supervisor will capture on site. Chioma's bungalow, Mon 4 Jan 2027 (WAT)."

Stage 1 inventory: CO-05. Priority P0 · FRs FR-12.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Milestone list · Plastering ready to claim | desktop | 1280×1060 | [desktop.png](desktop.png) |
| 2 | Claim confirmation | desktop | 1280×1060 | [desktop-02-claim-confirmation.png](desktop-02-claim-confirmation.png) |
| 3 | Claimed · waiting for the supervisor | desktop | 1280×1060 | [desktop-03-claimed-waiting-for-the-supervisor.png](desktop-03-claimed-waiting-for-the-supervisor.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Contractor top bar, Buttons, Status chip, Dialog and alert dialog, Escrow trust line, Ledger row and receipt, Milestone stepper, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |
| Dates | funded_at, claimed_at, verified_at, approved_at, released_at (UTC, shown in viewer time zone) |
| Supervisor checklist and notes | newest verification: checklist (JSONB), notes, decision |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Claim milestone", "Cancel".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/milestones`
- `POST /milestones/{id}/claim`

Navigates to: WEB-CONTRACTOR-003, WEB-CONTRACTOR-004, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009.

## 5. States and error cases

Designed states: Milestone list · Plastering ready to claim; Claim confirmation; Claimed · waiting for the supervisor.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `conflict_409`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.

Designer note on the board (`Con-Milestones.dc.html`), **Rules shown here**:

> "Claim milestone" appears only on a funded milestone, and only for the contractor on that project.
> The confirm step makes him tick every checklist item. This doesn't verify anything; it's to cut wasted supervisor visits.
> Once claimed, the claim can't be edited or withdrawn. The supervisor either verifies it or sends it back.
> Money is shown in naira only, because that's what he's paid in. The client's currency never appears in the contractor portal.

## 7. Responsive and accessibility notes

- Designed variants: desktop (3).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[3 working days]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
