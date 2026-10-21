---
id: WEB-CONTRACTOR-006
title: "Rework and dispute"
stage: 8
surface: web
role: contractor
priority: P0
fr: ["FR-12", "FR-14"]
route: "/c/projects/:id/milestones/:milestoneId"
suggested_target: "web/src/features/milestones/"
api: ["GET /projects/{id}/milestones", "POST /milestones/{id}/claim", "POST /milestones/{id}/disputes"]
links_to: ["WEB-CONTRACTOR-003", "WEB-CONTRACTOR-004", "WEB-CONTRACTOR-005", "WEB-CONTRACTOR-007", "WEB-CONTRACTOR-008", "WEB-CONTRACTOR-009"]
states: ["default", "rejected-with-reasons-wed-6-jan", "reworked-claim-again-mon-11-jan", "or-instead-dispute-the-rejection-thu-7-jan", "dispute-open", "loading", "error"]
inventory_refs: ["CO-07", "CO-08"]
missing_endpoints: ["MX-10"]
source_boards: ["Con-Rework.dc.html"]
---

# WEB-CONTRACTOR-006 · Rework and dispute

## 1. Purpose

Supervisor rejection with reasons, rework and claim again, or dispute the rejection and follow it.

From the approved board (`Con-Rework.dc.html`): "When the supervisor rejects a claim, the milestone goes back to Funded and the money stays held. The contractor sees exactly which items failed and why, with the supervisor's evidence. He can fix them and claim again, or, if he thinks the rejection is wrong, dispute it with iBackHome."

Stage 1 inventory: CO-07, CO-08. Priority P0 · FRs FR-12, FR-14.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Rejected with reasons · Wed 6 Jan | desktop | 1280×1000 | [desktop.png](desktop.png) |
| 2 | Reworked · claim again · Mon 11 Jan | desktop | 1280×1000 | [desktop-02-reworked-claim-again-mon-11-jan.png](desktop-02-reworked-claim-again-mon-11-jan.png) |
| 3 | Or instead: dispute the rejection · Thu 7 Jan | desktop | 1280×1000 | [desktop-03-or-instead-dispute-the-rejection-thu.png](desktop-03-or-instead-dispute-the-rejection-thu.png) |
| 4 | Dispute open | desktop | 1280×1000 | [desktop-04-dispute-open.png](desktop-04-dispute-open.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Contractor top bar, Buttons, Status chip, Alert and banner, Dialog and alert dialog, Escrow trust line, Evidence card, Checklist row, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Supervisor checklist and notes | newest verification: checklist (JSONB), notes, decision |
| Dispute reason and status | disputes.reason, disputes.status: open \| resolved_release \| resolved_reject |
| Resolution notes | disputes.resolution_notes, resolved_by |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Start rework", "Dispute this rejection", "Claim Plastering again", "+ Add", "Cancel", "Raise dispute".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/milestones`
- `POST /milestones/{id}/claim`
- `POST /milestones/{id}/disputes`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-10: Dispute reads and two-approver steps

Navigates to: WEB-CONTRACTOR-003, WEB-CONTRACTOR-004, WEB-CONTRACTOR-005, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009.

## 5. States and error cases

Designed states: Rejected with reasons · Wed 6 Jan; Reworked · claim again · Mon 11 Jan; Or instead: dispute the rejection · Thu 7 Jan; Dispute open.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Dispute resolution needs two different ops approvers; the first proposes, the second approves.
- Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.

## 7. Responsive and accessibility notes

- Designed variants: desktop (4).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Contractors can dispute a supervisor rejection (Stage 1 assumption, confirmed); the Spec allows contractor disputes but its state machine only shows disputes from verified.
- PLACEHOLDER values on this screen (in square brackets on the design): `[2 business days]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-10: Read a dispute with its timeline, list a project's disputes, and record the first ops proposal before the second approval. The Spec has raise, resolve and the ops queue.
