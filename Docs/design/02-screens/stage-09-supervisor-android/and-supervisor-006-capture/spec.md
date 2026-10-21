---
id: AND-SUPERVISOR-006
title: "Capture"
stage: 9
surface: android
role: supervisor
priority: P0
fr: ["FR-06", "FR-07", "FR-08"]
route: "CaptureScreen, CaptureReviewScreen"
suggested_target: "mobile/lib/features/capture/"
api: ["POST /evidence/upload-url", "POST /evidence"]
links_to: []
states: ["default", "ready-to-capture", "refused-gps-too-weak", "refused-mock-location", "warning-capturing-outside-site", "review-and-notes", "loading", "error"]
inventory_refs: ["SV-03", "SV-04", "SV-10"]
missing_endpoints: []
source_boards: ["Sup-Capture.dc.html"]
---

# AND-SUPERVISOR-006 · Capture

## 1. Purpose

In-app camera with the geofence bar and device checks; refused for weak GPS or mock location; warning outside the site; review and notes.

From the approved board (`Sup-Capture.dc.html`): "In-app camera only: there is no gallery or file picker anywhere in the app. Before the shutter works, three things must be true: GPS ±50 m or better, no mock location, and the device key ready. Outside the boundary, the app warns but still lets him shoot; the server rejects it. After the shot he links it to a checklist item and can add a note."

Stage 1 inventory: SV-03, SV-04, SV-10. Priority P0 · FRs FR-06, FR-07, FR-08.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Ready to capture | android | 360×800 | [android.png](android.png) |
| 2 | Refused · GPS too weak | android | 360×800 | [android-02-refused-gps-too-weak.png](android-02-refused-gps-too-weak.png) |
| 3 | Refused · mock location | android | 360×800 | [android-03-refused-mock-location.png](android-03-refused-mock-location.png) |
| 4 | Warning · capturing outside site | android | 360×800 | [android-04-warning-capturing-outside-site.png](android-04-warning-capturing-outside-site.png) |
| 5 | Review and notes | android | 360×800 | [android-05-review-and-notes.png](android-05-review-and-notes.png) |

Components (see [components.md](../../../01-design-system/components.md)): Android app bar and bottom nav, Buttons, Text input and select, Segmented control and tabs, Status chip, Alert and banner, Checklist row, Camera and capture bar, Sync row, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Thumbnail / media | GET /projects/{id}/evidence -> signed read URL (expires in 15 min), kind |
| Evidence ID | evidence.id (shown as EV-xxxx display ref) |
| Captured time | evidence.captured_at (UTC; client time zone, UTC on hover) |
| Captured by and role | captured_by -> users.full_name, captured_by_role |
| Status chip | evidence.status: pending_checks \| accepted \| flagged \| rejected |
| Three checks | per-check results (inside the site geofence, device-signed, not reused): see MX-07; until then derive from status + reject_reason |
| GPS point and accuracy | latitude, longitude, accuracy_m |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Retake", "Save".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /evidence/upload-url`
- `POST /evidence`

## 5. States and error cases

Designed states: Ready to capture; Refused · GPS too weak; Refused · mock location; Warning · capturing outside site; Review and notes.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.
- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.

## 7. Responsive and accessibility notes

- Designed variants: android (5).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
