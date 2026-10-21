---
id: WEB-CONTRACTOR-004
title: "BoQ editor"
stage: 8
surface: web
role: contractor
priority: P0
fr: ["FR-05"]
route: "/c/projects/:id/boq"
suggested_target: "web/src/features/projects/ (BoQ editor)"
api: ["GET /projects/{id}/boq", "PUT /projects/{id}/boq", "POST /projects/{id}/boq/approve", "POST /quotes/check"]
links_to: ["WEB-CONTRACTOR-003", "WEB-CONTRACTOR-005", "WEB-CONTRACTOR-007", "WEB-CONTRACTOR-008", "WEB-CONTRACTOR-009"]
states: ["default", "editing-version-2-validation-errors-wed-6-jan", "sent-back-sat-2-jan", "submitted-in-review-tue-29-dec", "loading", "error"]
inventory_refs: ["CO-03", "CO-04"]
missing_endpoints: ["MX-08"]
source_boards: ["Con-BoQ.dc.html"]
---

# WEB-CONTRACTOR-004 · BoQ editor

## 1. Purpose

Price the work as lines grouped into milestones, fix validation errors, submit; see it sent back with a reason or in review.

From the approved board (`Con-BoQ.dc.html`): "The contractor prices the work in naira, line by line, grouped into milestones. He types quantity and unit price; iBackHome's server works out every line total, milestone total and the grand total, so nobody can type a total that doesn't add up. Shown on Emeka's duplex: version 1 in review, sent back with comments, then version 2 being fixed."

Stage 1 inventory: CO-03, CO-04. Priority P0 · FRs FR-05.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Editing version 2 · validation errors · Wed 6 Jan | desktop | 1280×1220 | [desktop.png](desktop.png) |
| 2 | Sent back · Sat 2 Jan | desktop | 1280×1000 | [desktop-02-sent-back-sat-2-jan.png](desktop-02-sent-back-sat-2-jan.png) |
| 3 | Submitted · in review · Tue 29 Dec | desktop | 1280×860 | [desktop-03-submitted-in-review-tue-29-dec.png](desktop-03-submitted-in-review-tue-29-dec.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Contractor top bar, Buttons, Text input and select, Status chip, Alert and banner, Quote check result, Table, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Milestone groups and lines | GET /projects/{id}/boq -> milestone_sequence, milestone_name, line_no, description, unit, quantity, unit_price_minor, total_minor |
| BoQ total vs budget | boq totals + projects.budget_minor |
| Who has approved | boq_approvals[]: role, user, approved_at |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "+ Add line", "Submit version 2 for review", "Compare with version 1", "Revise BoQ".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/boq`
- `PUT /projects/{id}/boq`
- `POST /projects/{id}/boq/approve`
- `POST /quotes/check`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-08: Send the BoQ back

Navigates to: WEB-CONTRACTOR-003, WEB-CONTRACTOR-005, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009.

## 5. States and error cases

Designed states: Editing version 2 · validation errors · Wed 6 Jan; Sent back · Sat 2 Jan; Submitted · in review · Tue 29 Dec.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `boq_total_mismatch`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- BoQ line totals are computed by the server (422 boq_total_mismatch on mismatch); funding opens only after client, contractor and ops approve; the final approval needs a saved site (409 site_not_set).
- Every write sends an Idempotency-Key; disable the submit button while a write is in flight.

Designer note on the board (`Con-BoQ.dc.html`), **Validation rules the editor shows**:

> Line: description, unit and quantity are required; quantity above 0 with up to 3 decimals; unit price above ₦0.
> Milestone: at least one line. Lines can be dragged between milestones; none may be left unassigned.
> Total mismatch: the agreed contract sum must equal the lines total exactly. The server's figure wins.
> Errors are listed at the top as links that jump to the field, and each field says what's wrong in words, not just colour.
> The price index is shown as a hint while pricing. It never blocks submitting.

## 7. Responsive and accessibility notes

- Designed variants: desktop (3).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Limits: at most 20 milestones and 500 lines (Spec).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-08: The boq_review -> draft transition (client, contractor or ops, with a reason) has no endpoint.
