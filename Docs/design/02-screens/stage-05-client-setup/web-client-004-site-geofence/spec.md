---
id: WEB-CLIENT-004
title: "Site pin and geofence"
stage: 5
surface: web
role: client
priority: P0
fr: ["FR-04"]
route: "/projects/:id/site"
suggested_target: "web/src/features/projects/ (geofence drawing) + web/src/common/ (map component)"
api: ["PUT /projects/{id}/site", "GET /projects/{id}"]
links_to: ["WEB-CLIENT-020"]
states: ["default", "drawing-the-boundary", "error-pin-outside-the-boundary", "saved", "locked-project-active", "drawing", "locked", "loading", "error"]
inventory_refs: ["CS-04"]
missing_endpoints: []
source_boards: ["Setup-Site.dc.html"]
---

# WEB-CLIENT-004 · Site pin and geofence

## 1. Purpose

Pin the plot and draw the boundary polygon; shows the pin-outside error, saved and locked states.

From the approved board (`Setup-Site.dc.html`): "The client drops a pin on the plot and draws its boundary. The pin must be inside. The client can change the site while the project is in draft or BoQ review; once approved it locks, and only ops can change it. Every change is audited."

Stage 1 inventory: CS-04. Priority P0 · FRs FR-04.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Drawing the boundary | desktop | 1280×800 | [desktop.png](desktop.png) |
| 2 | Error — pin outside the boundary | desktop | 1280×800 | [desktop-02-error-pin-outside-the-boundary.png](desktop-02-error-pin-outside-the-boundary.png) |
| 3 | Saved | desktop | 1280×800 | [desktop-03-saved.png](desktop-03-saved.png) |
| 4 | Locked — project active | desktop | 1280×800 | [desktop-04-locked-project-active.png](desktop-04-locked-project-active.png) |
| 5 | Drawing | mobile | 390×844 | [mobile.png](mobile.png) |
| 6 | Locked | mobile | 390×844 | [mobile-02-locked.png](mobile-02-locked.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Buttons, Status chip, Geofence map, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Site pin | sites.location (POINT, GeoJSON) via PUT /projects/{id}/site |
| Boundary polygon | sites.geofence (POLYGON, SRID 4326) |
| 25 m tolerance band | fixed rule from the Spec (ST_Buffer 25 m), drawn client-side |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Boundary", "Undo", "Clear", "Save site", "Back to set-up", "Edit site", "Ask our team to change it".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `PUT /projects/{id}/site`
- `GET /projects/{id}`

Navigates to: WEB-CLIENT-020.

## 5. States and error cases

Designed states: Drawing the boundary; Error — pin outside the boundary; Saved; Locked — project active; Drawing; Locked.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `pin_outside_geofence`, `site_locked`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- The client can set or change the site only in draft or boq_review (409 site_locked after); the pin must be inside the polygon (422 pin_outside_geofence).
- The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.

## 7. Responsive and accessibility notes

- Designed variants: desktop (4), mobile (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Map tiles provider is not in the Spec.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
