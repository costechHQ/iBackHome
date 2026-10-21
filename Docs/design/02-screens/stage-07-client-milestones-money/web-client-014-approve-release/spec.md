---
id: WEB-CLIENT-014
title: "Approve a release"
stage: 7
surface: web
role: client
priority: P0
fr: ["FR-14", "FR-15"]
route: "/projects/:id/milestones/:milestoneId/approve"
suggested_target: "web/src/features/milestones/"
api: ["POST /milestones/{id}/approve", "GET /projects/{id}/milestones", "GET /projects/{id}/ledger"]
links_to: ["WEB-CLIENT-005", "WEB-CLIENT-009", "WEB-CLIENT-010", "WEB-CLIENT-011", "WEB-CLIENT-012", "WEB-CLIENT-013", "WEB-CLIENT-017", "WEB-CLIENT-018", "WEB-CLIENT-019", "WEB-CLIENT-020"]
states: ["default", "1-home-the-approval-card", "2-review", "3-confirm", "pending-release", "released-receipt", "confirm-dialog", "released-with-receipt", "loading", "error"]
inventory_refs: ["CM-03"]
missing_endpoints: ["MX-22"]
source_boards: ["Ms-Approve.dc.html"]
---

# WEB-CLIENT-014 · Approve a release

## 1. Purpose

Approve a verified milestone in three taps on mobile web (card, review, confirm), then pending release and the receipt; desktop dialog and receipt.

From the approved board (`Ms-Approve.dc.html`): "Review, approve, confirm. The confirm step repeats the amount in both currencies, the payee and the bank, because a release can't be undone. Then the screen follows the money until the escrow partner confirms, and ends with a receipt. Sat 12 Dec, Chioma in Manchester (GMT)."

Stage 1 inventory: CM-03. Priority P0 · FRs FR-14, FR-15.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | 1 · Home: the approval card | mobile | 390×844 | [mobile.png](mobile.png) |
| 2 | 2 · Review | mobile | 390×844 | [mobile-02-2-review.png](mobile-02-2-review.png) |
| 3 | 3 · Confirm | mobile | 390×844 | [mobile-03-3-confirm.png](mobile-03-3-confirm.png) |
| 4 | Pending release | mobile | 390×844 | [mobile-04-pending-release.png](mobile-04-pending-release.png) |
| 5 | Released · receipt | mobile | 390×844 | [mobile-05-released-receipt.png](mobile-05-released-receipt.png) |
| 6 | Confirm dialog | desktop | 1280×800 | [desktop.png](desktop.png) |
| 7 | Released, with receipt | desktop | 1280×800 | [desktop-02-released-with-receipt.png](desktop-02-released-with-receipt.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Project tabs, Client bottom nav, Buttons, Status chip, Dialog and alert dialog, Money display, Escrow trust line, Ledger row and receipt, Milestone detail panel (MsDetail), Evidence card, Three-checks list, Checklist row, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |
| Dates | funded_at, claimed_at, verified_at, approved_at, released_at (UTC, shown in viewer time zone) |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |
| Escrow trust line | static copy: "Held by a licensed escrow partner, never by iBackHome." |
| Release status | escrow_releases.status: requested \| submitted \| released \| failed |
| Paid to | contractor business name + payout_recipients.account_number_masked |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Review and approve", "Approve release", "Raise a dispute", "Confirm and release", "Cancel", "Download receipt (PDF)", "Fund Plastering", "Back to my project", "Download PDF".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /milestones/{id}/approve`
- `GET /projects/{id}/milestones`
- `GET /projects/{id}/ledger`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-22: Receipts and exports

Navigates to: WEB-CLIENT-005, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-013, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020.

## 5. States and error cases

Designed states: 1 · Home: the approval card; 2 · Review; 3 · Confirm; Pending release; Released · receipt; Confirm dialog; Released, with receipt.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `milestone_not_verified`, `conflict_409`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.

## 7. Responsive and accessibility notes

- Designed variants: mobile (5), desktop (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- "Taking longer than [1 hour]" threshold is PLACEHOLDER.
- Receipt PDF has no endpoint (MX-22).
- PLACEHOLDER values on this screen (in square brackets on the design): `[1 hour]`, `[partner ref]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-22: Release receipt PDF, ledger CSV export and audit log export. No endpoints in the Spec.
