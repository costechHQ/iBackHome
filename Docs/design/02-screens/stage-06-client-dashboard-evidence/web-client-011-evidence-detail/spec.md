---
id: WEB-CLIENT-011
title: "Evidence detail"
stage: 6
surface: web
role: client
priority: P0
fr: ["FR-07", "FR-08", "FR-10"]
route: "/projects/:id/evidence/:evidenceId"
suggested_target: "web/src/features/dashboard/"
api: ["GET /projects/{id}/evidence"]
links_to: ["WEB-CLIENT-010", "WEB-CLIENT-012", "WEB-CLIENT-020"]
states: ["default", "accepted-supervisor-video-utc-shown-on-hover", "uploaded-by-the-contractor", "flagged-as-the-client-sees-it", "accepted", "under-review", "loading", "error"]
inventory_refs: ["CD-03"]
missing_endpoints: ["MX-07"]
source_boards: ["Dash-EvidenceDetail.dc.html"]
---

# WEB-CLIENT-011 · Evidence detail

## 1. Purpose

Full photo or video, capture point on the site map, time in the client's zone with UTC on hover, the three checks, who captured it; contractor-upload and under-review variants.

From the approved board (`Dash-EvidenceDetail.dc.html`): "The proof, and why it can be trusted: where it was taken relative to the site boundary, when (in the viewer's time zone, UTC on hover), by whom, and the three checks. Contractor uploads and items under review are labelled so nobody mistakes them for verified proof."

Stage 1 inventory: CD-03. Priority P0 · FRs FR-07, FR-08, FR-10.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Accepted supervisor video · UTC shown on hover | desktop | 1280×940 | [desktop.png](desktop.png) |
| 2 | Uploaded by the contractor | desktop | 1280×940 | [desktop-02-uploaded-by-the-contractor.png](desktop-02-uploaded-by-the-contractor.png) |
| 3 | Flagged — as the client sees it | desktop | 1280×940 | [desktop-03-flagged-as-the-client-sees-it.png](desktop-03-flagged-as-the-client-sees-it.png) |
| 4 | Accepted | mobile | 390×940 | [mobile.png](mobile.png) |
| 5 | Under review | mobile | 390×940 | [mobile-02-under-review.png](mobile-02-under-review.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Status chip, Evidence card, Three-checks list, Geofence map, Card.

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

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/evidence`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-07: Evidence detail and per-check results

Navigates to: WEB-CLIENT-010, WEB-CLIENT-012, WEB-CLIENT-020.

## 5. States and error cases

Designed states: Accepted supervisor video · UTC shown on hover; Uploaded by the contractor; Flagged — as the client sees it; Accepted; Under review.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- A flagged item goes to ops and never rejects a milestone by itself.

## 7. Responsive and accessibility notes

- Designed variants: desktop (3), mobile (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Personal EXIF data is stripped from what clients see (Spec).
- PLACEHOLDER values on this screen (in square brackets on the design): `[Video · EV-2119 · full size]`, `[Photo · EV-2102 · full size]`, `[Photo · EV-2121 · full size]`, `[Photo · tap to enlarge]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-07: Read one evidence item with the three check results (geofence, signature, reuse), its milestone and capture metadata. The gallery list returns status and reject_reason only.
