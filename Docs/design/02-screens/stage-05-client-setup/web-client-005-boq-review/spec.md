---
id: WEB-CLIENT-005
title: "BoQ review and approval"
stage: 5
surface: web
role: client
priority: P0
fr: ["FR-05"]
route: "/projects/:id/boq"
suggested_target: "web/src/features/projects/"
api: ["GET /projects/{id}/boq", "POST /projects/{id}/boq/approve"]
links_to: ["WEB-CLIENT-020"]
states: ["default", "cs-06-boq-review-over-budget-waiting-for-the-cli", "cs-08-send-back-for-changes", "all-three-approved-project-active", "boq-summary", "confirm-approval", "loading", "error"]
inventory_refs: ["CS-06", "CS-08"]
missing_endpoints: ["MX-08"]
source_boards: ["Setup-BoQ.dc.html"]
---

# WEB-CLIENT-005 · BoQ review and approval

## 1. Purpose

Review the BoQ grouped by milestone against the budget, see who has approved, approve or send back with a reason.

From the approved board (`Setup-BoQ.dc.html`): "The contractor prices the work in naira, grouped into milestones. iBackHome computes every total from quantity × unit price. Client, contractor and ops each approve; the last approval creates the milestones and makes the project active. Client-currency figures before funding are estimates."

Stage 1 inventory: CS-06, CS-08. Priority P0 · FRs FR-05.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | CS-06 · BoQ review — over budget, waiting for the client | desktop | 1280×1460 | [desktop.png](desktop.png) |
| 2 | CS-08 · Send back for changes | desktop | 1280×800 | [desktop-02-cs-08-send-back-for-changes.png](desktop-02-cs-08-send-back-for-changes.png) |
| 3 | All three approved — project active | desktop | 1280×800 | [desktop-03-all-three-approved-project-active.png](desktop-03-all-three-approved-project-active.png) |
| 4 | BoQ summary | mobile | 390×844 | [mobile.png](mobile.png) |
| 5 | Confirm approval | mobile | 390×700 | [mobile-02-confirm-approval.png](mobile-02-confirm-approval.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Buttons, Text input and select, Status chip, Dialog and alert dialog, Money display, Escrow trust line, Milestone stepper, Quote check result, Table, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Milestone groups and lines | GET /projects/{id}/boq -> milestone_sequence, milestone_name, line_no, description, unit, quantity, unit_price_minor, total_minor |
| BoQ total vs budget | boq totals + projects.budget_minor |
| Who has approved | boq_approvals[]: role, user, approved_at |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "1 · Foundation · 6 lines ₦10,530,000", "3 · Roofing · 18 lines · 1 flagged ₦13,260,000", "4 · Plastering · 14 lines ₦7,605,000", "5 · Finishing · 21 lines ₦14,820,000", "Approve BoQ", "Send back for changes", "Keep reviewing", "Send back", "Fund this milestone", "Not yet".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/boq`
- `POST /projects/{id}/boq/approve`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-08: Send the BoQ back

Navigates to: WEB-CLIENT-020.

## 5. States and error cases

Designed states: CS-06 · BoQ review — over budget, waiting for the client; CS-08 · Send back for changes; All three approved — project active; BoQ summary; Confirm approval.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `site_not_set`, `conflict_409`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- BoQ line totals are computed by the server (422 boq_total_mismatch on mismatch); funding opens only after client, contractor and ops approve; the final approval needs a saved site (409 site_not_set).
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.

## 7. Responsive and accessibility notes

- Designed variants: desktop (3), mobile (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Client-currency figures are estimates until funding (Stage 1 assumption).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-08: The boq_review -> draft transition (client, contractor or ops, with a reason) has no endpoint.
