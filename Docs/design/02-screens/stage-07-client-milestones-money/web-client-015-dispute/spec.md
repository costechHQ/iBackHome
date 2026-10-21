---
id: WEB-CLIENT-015
title: "Raise a dispute and outcomes"
stage: 7
surface: web
role: client
priority: P0
fr: ["FR-14"]
route: "/projects/:id/milestones/:milestoneId/dispute"
suggested_target: "web/src/features/milestones/"
api: ["POST /milestones/{id}/disputes", "GET /projects/{id}/milestones"]
links_to: ["WEB-CLIENT-005", "WEB-CLIENT-009", "WEB-CLIENT-010", "WEB-CLIENT-011", "WEB-CLIENT-012", "WEB-CLIENT-013", "WEB-CLIENT-017", "WEB-CLIENT-018", "WEB-CLIENT-019", "WEB-CLIENT-020"]
states: ["default", "raise-a-dispute", "release-paused", "outcome-a-released", "outcome-b-rework-required", "raise-a-dispute", "milestone-with-release-paused", "dispute-page-both-outcomes", "loading", "error"]
inventory_refs: ["CM-04", "CM-05"]
missing_endpoints: ["MX-10"]
source_boards: ["Ms-Dispute.dc.html"]
---

# WEB-CLIENT-015 · Raise a dispute and outcomes

## 1. Purpose

Raise a dispute on a verified milestone, see the release paused, and the two outcomes (released, or rework required).

From the approved board (`Ms-Dispute.dc.html`): "The other path from Verified: instead of approving Roofing on Sat 12 Dec, Chioma raises a dispute. The release pauses, the money stays with the escrow partner, and iBackHome decides: release, or rework. A release decision needs two people from our team to agree."

Stage 1 inventory: CM-04, CM-05. Priority P0 · FRs FR-14.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Raise a dispute | mobile | 390×844 | [mobile.png](mobile.png) |
| 2 | Release paused | mobile | 390×844 | [mobile-02-release-paused.png](mobile-02-release-paused.png) |
| 3 | Outcome A · released | mobile | 390×844 | [mobile-03-outcome-a-released.png](mobile-03-outcome-a-released.png) |
| 4 | Outcome B · rework required | mobile | 390×844 | [mobile-04-outcome-b-rework-required.png](mobile-04-outcome-b-rework-required.png) |
| 5 | Raise a dispute | desktop | 1280×844 | [desktop.png](desktop.png) |
| 6 | Milestone with release paused | desktop | 1280×1200 | [desktop-02-milestone-with-release-paused.png](desktop-02-milestone-with-release-paused.png) |
| 7 | Dispute page, both outcomes | desktop | 1280×1200 | [desktop-03-dispute-page-both-outcomes.png](desktop-03-dispute-page-both-outcomes.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Project tabs, Client bottom nav, Buttons, Status chip, Alert and banner, Dialog and alert dialog, Money display, Escrow trust line, Ledger row and receipt, Milestone detail panel (MsDetail), Evidence card, Three-checks list, Checklist row, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Dispute reason and status | disputes.reason, disputes.status: open \| resolved_release \| resolved_reject |
| Resolution notes | disputes.resolution_notes, resolved_by |
| Timeline | audit log entries for the dispute: see MX-10 |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "+ Add", "Raise dispute and pause release", "View receipt R-3321", "Go to Roofing", "Approve release", "Raise a dispute", "Cancel", "Raise dispute", "View dispute D-0057".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /milestones/{id}/disputes`
- `GET /projects/{id}/milestones`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-10: Dispute reads and two-approver steps

Navigates to: WEB-CLIENT-005, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-013, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020.

## 5. States and error cases

Designed states: Raise a dispute; Release paused; Outcome A · released; Outcome B · rework required; Raise a dispute; Milestone with release paused; Dispute page, both outcomes.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `conflict_409`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Dispute resolution needs two different ops approvers; the first proposes, the second approves.
- Every write sends an Idempotency-Key; disable the submit button while a write is in flight.

## 7. Responsive and accessibility notes

- Designed variants: mobile (4), desktop (3).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[2 business days]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-10: Read a dispute with its timeline, list a project's disputes, and record the first ops proposal before the second approval. The Spec has raise, resolve and the ops queue.
