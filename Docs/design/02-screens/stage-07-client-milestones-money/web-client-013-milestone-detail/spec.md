---
id: WEB-CLIENT-013
title: "Milestone detail (every state)"
stage: 7
surface: web
role: client
priority: P0
fr: ["FR-12", "FR-14", "FR-15"]
route: "/projects/:id/milestones/:milestoneId"
suggested_target: "web/src/features/milestones/"
api: ["GET /projects/{id}/milestones", "GET /projects/{id}/evidence", "GET /projects/{id}/ledger"]
links_to: ["WEB-CLIENT-005", "WEB-CLIENT-009", "WEB-CLIENT-010", "WEB-CLIENT-011", "WEB-CLIENT-012", "WEB-CLIENT-017", "WEB-CLIENT-018", "WEB-CLIENT-019", "WEB-CLIENT-020"]
states: ["default", "pending-plastering-not-funded-yet", "funded-plastering-work-can-start", "claimed-roofing-waiting-for-the-supervisor", "verified-roofing-needs-your-approval", "disputed-roofing-release-paused", "released-blockwork-to-lintel", "verified", "pending", "loading", "error"]
inventory_refs: ["CM-01", "CM-02"]
missing_endpoints: ["MX-07", "MX-20"]
source_boards: ["Ms-Detail.dc.html"]
---

# WEB-CLIENT-013 · Milestone detail (every state)

## 1. Purpose

One milestone in each state (pending, funded, claimed, verified, disputed, released) with the two-key release panel, checklist and evidence.

From the approved board (`Ms-Detail.dc.html`): "One layout for all six states, so the client always knows where to look: where the milestone is, what happens next, the checklist the supervisor must capture, his verification, and where the money is. Only Verified asks the client to act on the release; Pending asks them to fund."

Stage 1 inventory: CM-01, CM-02. Priority P0 · FRs FR-12, FR-14, FR-15.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Pending · Plastering, not funded yet | desktop | 1280×1200 | [desktop.png](desktop.png) |
| 2 | Funded · Plastering, work can start | desktop | 1280×1200 | [desktop-02-funded-plastering-work-can-start.png](desktop-02-funded-plastering-work-can-start.png) |
| 3 | Claimed · Roofing, waiting for the supervisor | desktop | 1280×1200 | [desktop-03-claimed-roofing-waiting-for-the-supe.png](desktop-03-claimed-roofing-waiting-for-the-supe.png) |
| 4 | Verified · Roofing, needs your approval | desktop | 1280×1200 | [desktop-04-verified-roofing-needs-your-approval.png](desktop-04-verified-roofing-needs-your-approval.png) |
| 5 | Disputed · Roofing, release paused | desktop | 1280×1200 | [desktop-05-disputed-roofing-release-paused.png](desktop-05-disputed-roofing-release-paused.png) |
| 6 | Released · Blockwork to Lintel | desktop | 1280×1200 | [desktop-06-released-blockwork-to-lintel.png](desktop-06-released-blockwork-to-lintel.png) |
| 7 | Verified | mobile | 390×1560 | [mobile.png](mobile.png) |
| 8 | Pending | mobile | 390×1400 | [mobile-02-pending.png](mobile-02-pending.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Project tabs, Buttons, Status chip, Alert and banner, Money display, Escrow trust line, Ledger row and receipt, Milestone detail panel (MsDetail), Evidence card, Three-checks list, Checklist row, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |
| Dates | funded_at, claimed_at, verified_at, approved_at, released_at (UTC, shown in viewer time zone) |
| Supervisor checklist and notes | newest verification: checklist (JSONB), notes, decision |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |
| Escrow trust line | static copy: "Held by a licensed escrow partner, never by iBackHome." |
| Release status | escrow_releases.status: requested \| submitted \| released \| failed |
| Paid to | contractor business name + payout_recipients.account_number_masked |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Fund this milestone", "See contractor uploads", "Approve release", "Raise a dispute", "View dispute D-0057", "View receipt R-3215", "Download PDF", "Fund Plastering".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/milestones`
- `GET /projects/{id}/evidence`
- `GET /projects/{id}/ledger`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-07: Evidence detail and per-check results
- MX-20: Escrow balance per project

Navigates to: WEB-CLIENT-005, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020.

## 5. States and error cases

Designed states: Pending · Plastering, not funded yet; Funded · Plastering, work can start; Claimed · Roofing, waiting for the supervisor; Verified · Roofing, needs your approval; Disputed · Roofing, release paused; Released · Blockwork to Lintel; Verified; Pending.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- Status colour appears only in chips and alerts, and every state also differs by text or shape.

Designer note on the board (`Ms-Detail.dc.html`), **Rules shown here**:

> Only the supervisor's own captures fill the checklist. Contractor uploads are listed for information only.
> Approve and dispute appear only on Verified. While a dispute is open there is no approve button anywhere.
> Status colour sits only in chips and alert banners; the stepper uses shape (lock, hand, check, scales) as well as colour.

## 7. Responsive and accessibility notes

- Designed variants: desktop (6), mobile (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[2 business days]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-07: Read one evidence item with the three check results (geofence, signature, reuse), its milestone and capture metadata. The gallery list returns status and reject_reason only.
- MX-20: The "in escrow now" figure. escrow_accounts.balance_minor exists but no endpoint returns it; it may be derived from GET /projects/{id}/ledger.
