---
id: WEB-CLIENT-010
title: "Evidence gallery"
stage: 6
surface: web
role: client
priority: P0
fr: ["FR-06", "FR-07", "FR-08", "FR-09", "FR-10", "FR-15"]
route: "/projects/:id/evidence"
suggested_target: "web/src/features/dashboard/"
api: ["GET /projects/{id}/evidence"]
links_to: ["WEB-CLIENT-009", "WEB-CLIENT-011", "WEB-CLIENT-012", "WEB-CLIENT-020"]
states: ["default", "gallery", "empty-filters-match-nothing", "gallery", "filters-sheet", "loading", "error"]
inventory_refs: ["CD-02"]
missing_endpoints: []
source_boards: ["Dash-Evidence.dc.html"]
---

# WEB-CLIENT-010 · Evidence gallery

## 1. Purpose

Filter evidence by milestone, date, who captured it and type; grid of evidence cards; empty state when filters match nothing.

From the approved board (`Dash-Evidence.dc.html`): "Everything captured on site, newest first, grouped by day in the client's time zone. Clients see accepted evidence and items under review; rejected captures never appear here. Photos are placeholders."

Stage 1 inventory: CD-02. Priority P0 · FRs FR-06, FR-07, FR-08, FR-09, FR-10, FR-15.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Gallery | desktop | 1280×1140 | [desktop.png](desktop.png) |
| 2 | Empty (filters match nothing) | desktop | 1280×520 | [desktop-02-empty-filters-match-nothing.png](desktop-02-empty-filters-match-nothing.png) |
| 3 | Gallery | mobile | 390×900 | [mobile.png](mobile.png) |
| 4 | Filters sheet | mobile | 390×760 | [mobile-02-filters-sheet.png](mobile-02-filters-sheet.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Project tabs, Client bottom nav, Buttons, Search and filters, Status chip, Empty state, Dialog and alert dialog, Bottom sheet and side panel, Evidence card, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Thumbnail / media | GET /projects/{id}/evidence -> signed read URL (expires in 15 min), kind |
| Evidence ID | evidence.id (shown as EV-xxxx display ref) |
| Captured time | evidence.captured_at (UTC; client time zone, UTC on hover) |
| Captured by and role | captured_by -> users.full_name, captured_by_role |
| Status chip | evidence.status: pending_checks \| accepted \| flagged \| rejected |
| Milestone | evidence.milestone |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Supervisor", "Contractor", "Photos", "Videos", "Load more", "Clear filters", "Filters · 1", "Clear", "Show 21 items".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/evidence`

Navigates to: WEB-CLIENT-009, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-020.

## 5. States and error cases

Designed states: Gallery; Empty (filters match nothing); Gallery; Filters sheet.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- A flagged item goes to ops and never rejects a milestone by itself.

## 7. Responsive and accessibility notes

- Designed variants: desktop (2), mobile (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Filter parameters for GET /projects/{id}/evidence are not defined in the Spec.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
