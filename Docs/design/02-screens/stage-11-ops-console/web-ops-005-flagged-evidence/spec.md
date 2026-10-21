---
id: WEB-OPS-005
title: "Flagged evidence review"
stage: 11
surface: web
role: ops
priority: P0
fr: ["FR-10", "FR-19"]
route: "/ops/evidence/:id"
suggested_target: "web/src/features/ops-console/"
api: ["GET /ops/queue", "POST /evidence/{id}/decision"]
links_to: []
states: ["default", "flagged-evidence-review", "loading", "error"]
inventory_refs: ["OP-07"]
missing_endpoints: ["MX-07"]
source_boards: ["Op-Evidence.dc.html"]
---

# WEB-OPS-005 · Flagged evidence review

## 1. Purpose

Side-by-side near-duplicate match with distance and metadata; accept or reject (rejecting needs notes).

From the approved board (`Op-Evidence.dc.html`): "A near-duplicate check (perceptual hash) flags any capture that looks like an earlier one. The reviewer sees the two images side by side with the similarity distance, every piece of metadata, and both points on the site map, then accepts or rejects. Notes are required either way."

Stage 1 inventory: OP-07. Priority P0 · FRs FR-10, FR-19.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Flagged evidence review | desktop | 1440×900 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Text input and select, Search and filters, Status chip, Evidence card, Checklist row, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Thumbnail / media | GET /projects/{id}/evidence -> signed read URL (expires in 15 min), kind |
| Evidence ID | evidence.id (shown as EV-xxxx display ref) |
| Captured time | evidence.captured_at (UTC; client time zone, UTC on hover) |
| Captured by and role | captured_by -> users.full_name, captured_by_role |
| Status chip | evidence.status: pending_checks \| accepted \| flagged \| rejected |
| Milestone | evidence.milestone |
| Three checks | per-check results (inside the site geofence, device-signed, not reused): see MX-07; until then derive from status + reject_reason |
| GPS point and accuracy | latitude, longitude, accuracy_m |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Accept", "Reject".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /ops/queue`
- `POST /evidence/{id}/decision`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-07: Evidence detail and per-check results

## 5. States and error cases

Designed states: Flagged evidence review.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A flagged item goes to ops and never rejects a milestone by itself.
- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- Every money movement and sensitive action is audit-logged; the audit log is read-only.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- CONFLICT TO DECIDE: the approved board and Stage 13 assumptions flag at a distance of 10 or less out of 64; the Spec says 8 or less. Keep the threshold a server config value defaulting to the Spec (8) until Gabriel confirms; show the configured value in this screen (see PACKAGE-REPORT).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-07: Read one evidence item with the three check results (geofence, signature, reuse), its milestone and capture metadata. The gallery list returns status and reject_reason only.
