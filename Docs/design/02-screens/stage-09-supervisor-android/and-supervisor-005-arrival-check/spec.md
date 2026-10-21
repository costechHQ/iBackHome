---
id: AND-SUPERVISOR-005
title: "Arrival check"
stage: 9
surface: android
role: supervisor
priority: P0
fr: ["FR-08"]
route: "ArrivalScreen"
suggested_target: "mobile/lib/features/capture/"
api: ["GET /projects/{id}"]
links_to: []
states: ["default", "finding-your-location", "inside-the-site-boundary", "outside-the-site-boundary", "loading", "error"]
inventory_refs: ["SV-02", "SV-10"]
missing_endpoints: []
source_boards: ["Sup-Arrival.dc.html"]
---

# AND-SUPERVISOR-005 · Arrival check

## 1. Purpose

Confirm the supervisor is inside the site boundary before capturing: finding location, inside, outside.

From the approved board (`Sup-Arrival.dc.html`): "Before the first capture, the app checks where he is against the site's locked boundary and the 25 m GPS tolerance (dashed). The phone only warns; the server makes the final decision on every capture."

Stage 1 inventory: SV-02, SV-10. Priority P0 · FRs FR-08.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Finding your location | android | 360×800 | [android.png](android.png) |
| 2 | Inside the site boundary | android | 360×800 | [android-02-inside-the-site-boundary.png](android-02-inside-the-site-boundary.png) |
| 3 | Outside the site boundary | android | 360×800 | [android-03-outside-the-site-boundary.png](android-03-outside-the-site-boundary.png) |

Components (see [components.md](../../../01-design-system/components.md)): Android app bar and bottom nav, Buttons, Alert and banner, Geofence map, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Site pin | sites.location (POINT, GeoJSON) via PUT /projects/{id}/site |
| Boundary polygon | sites.geofence (POLYGON, SRID 4326) |
| 25 m tolerance band | fixed rule from the Spec (ST_Buffer 25 m), drawn client-side |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Start capturing", "Check again", "Directions to site".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}`

## 5. States and error cases

Designed states: Finding your location; Inside the site boundary; Outside the site boundary.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.

## 7. Responsive and accessibility notes

- Designed variants: android (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
