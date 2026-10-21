---
id: WEB-CLIENT-012
title: "Project site map"
stage: 6
surface: web
role: client
priority: P0
fr: ["FR-04"]
route: "/projects/:id/site-map"
suggested_target: "web/src/features/dashboard/ + web/src/common/ (map component)"
api: ["GET /projects/{id}", "GET /projects/{id}/evidence"]
links_to: ["WEB-CLIENT-011", "WEB-CLIENT-020"]
states: ["default", "desktop", "mobile-web", "loading", "error"]
inventory_refs: ["CD-03"]
missing_endpoints: []
source_boards: ["Dash-SiteMap.dc.html"]
---

# WEB-CLIENT-012 · Project site map

## 1. Purpose

Read-only site map with the geofence, 25 m tolerance band, site pin and capture points by status.

From the approved board (`Dash-SiteMap.dc.html`): "The locked boundary with every capture placed where it was taken. Shapes, not just colour, tell them apart: filled dot for supervisor evidence, ring for contractor uploads, flag for items under review."

Stage 1 inventory: CD-03. Priority P0 · FRs FR-04.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×880 | [desktop.png](desktop.png) |
| 2 | Mobile web | mobile | 390×880 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Client bottom nav, Status chip, Geofence map, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Site pin | sites.location (POINT, GeoJSON) via PUT /projects/{id}/site |
| Boundary polygon | sites.geofence (POLYGON, SRID 4326) |
| 25 m tolerance band | fixed rule from the Spec (ST_Buffer 25 m), drawn client-side |
| Thumbnail / media | GET /projects/{id}/evidence -> signed read URL (expires in 15 min), kind |
| Evidence ID | evidence.id (shown as EV-xxxx display ref) |
| Captured time | evidence.captured_at (UTC; client time zone, UTC on hover) |
| Captured by and role | captured_by -> users.full_name, captured_by_role |
| Status chip | evidence.status: pending_checks \| accepted \| flagged \| rejected |
| GPS point and accuracy | latitude, longitude, accuracy_m |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Roofing", "Open evidence".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}`
- `GET /projects/{id}/evidence`

Navigates to: WEB-CLIENT-011, WEB-CLIENT-020.

## 5. States and error cases

Designed states: Desktop; Mobile web.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- The client can set or change the site only in draft or boq_review (409 site_locked after); the pin must be inside the polygon (422 pin_outside_geofence).
- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
