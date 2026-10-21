---
id: WEB-OPS-006
title: "Disputes and two-approver resolution"
stage: 11
surface: web
role: ops
priority: P0
fr: ["FR-14", "FR-19", "FR-23"]
route: "/ops/disputes, /ops/disputes/:id"
suggested_target: "web/src/features/ops-console/"
api: ["GET /ops/queue", "POST /disputes/{id}/resolve"]
links_to: []
states: ["default", "dispute-queue", "resolution-two-approver-flow", "loading", "error"]
inventory_refs: ["OP-08"]
missing_endpoints: ["MX-10"]
source_boards: ["Op-Disputes.dc.html"]
---

# WEB-OPS-006 · Disputes and two-approver resolution

## 1. Purpose

Dispute queue and resolution: timeline, evidence, first ops proposes, a different ops person approves.

From the approved board (`Op-Disputes.dc.html`): "Each dispute has its full timeline, the evidence on both sides and the money held. A release needs two different ops people: Adaeze proposed it, and Ngozi (signed in) is the second approver. Rework needs one decision. D-0064 is the dispute that stopped Chidi's offline verification in Stage 9 and held Ugwu's O-0149 payment in Stage 10."

Stage 1 inventory: OP-08. Priority P0 · FRs FR-14, FR-19, FR-23.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Dispute queue | desktop | 1440×900 | [desktop.png](desktop.png) |
| 2 | Resolution · two-approver flow | desktop | 1440×900 | [desktop-02-resolution-two-approver-flow.png](desktop-02-resolution-two-approver-flow.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Text input and select, Segmented control and tabs, Search and filters, Status chip, Alert and banner, Escrow trust line, Evidence card, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Dispute reason and status | disputes.reason, disputes.status: open \| resolved_release \| resolved_reject |
| Resolution notes | disputes.resolution_notes, resolved_by |
| Timeline | audit log entries for the dispute: see MX-10 |
| Thumbnail / media | GET /projects/{id}/evidence -> signed read URL (expires in 15 min), kind |
| Evidence ID | evidence.id (shown as EV-xxxx display ref) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Approve release", "Disagree".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /ops/queue`
- `POST /disputes/{id}/resolve`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-10: Dispute reads and two-approver steps

## 5. States and error cases

Designed states: Dispute queue; Resolution · two-approver flow.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Dispute resolution needs two different ops approvers; the first proposes, the second approves.
- A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- Every money movement and sensitive action is audit-logged; the audit log is read-only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."

## 7. Responsive and accessibility notes

- Designed variants: desktop (2).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[2 business days]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-10: Read a dispute with its timeline, list a project's disputes, and record the first ops proposal before the second approval. The Spec has raise, resolve and the ops queue.
