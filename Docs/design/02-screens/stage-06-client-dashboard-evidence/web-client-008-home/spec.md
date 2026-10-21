---
id: WEB-CLIENT-008
title: "Home: needs your attention"
stage: 6
surface: web
role: client
priority: P0
fr: ["FR-15"]
route: "/"
suggested_target: "web/src/features/dashboard/"
api: ["GET /projects", "GET /projects/{id}/milestones", "GET /projects/{id}/reports"]
links_to: ["WEB-CLIENT-009", "WEB-CLIENT-014", "WEB-CLIENT-020"]
states: ["default", "desktop", "mobile-web", "loading", "error"]
inventory_refs: ["CD-01"]
missing_endpoints: ["MX-02", "MX-11"]
source_boards: ["Dash-Home.dc.html"]
---

# WEB-CLIENT-008 · Home: needs your attention

## 1. Purpose

Several projects at a glance with a "needs your attention" area (approvals, reports, expiring invitations).

From the approved board (`Dash-Home.dc.html`): "Anything waiting on the client comes first, across all projects, most urgent at the top. Money actions lead. Sample dates are in December 2026, mid-build."

Stage 1 inventory: CD-01. Priority P0 · FRs FR-15.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×940 | [desktop.png](desktop.png) |
| 2 | Mobile web | mobile | 390×940 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Client bottom nav, Buttons, Status chip, Money display, Escrow trust line, Reviewed-by badge, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Project cards | GET /projects -> items[]: id, title, address, status, budget_minor, currency |
| Next action per project | derived from milestones[].status (verified -> approve) |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "New project", "Review and approve", "Read report", "Resend invitation".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects`
- `GET /projects/{id}/milestones`
- `GET /projects/{id}/reports`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-02: Project invitations
- MX-11: In-app notification feed

Navigates to: WEB-CLIENT-009, WEB-CLIENT-014, WEB-CLIENT-020.

## 5. States and error cases

Designed states: Desktop; Mobile web.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-02: View, accept, decline, resend and cancel an invitation (contractor by client; supplier and ops user by ops). The Spec only says POST /projects "invites contractor".
- MX-11: List the signed-in user's notifications and mark them read (notifications table exists, no endpoint).
