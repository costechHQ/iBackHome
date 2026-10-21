---
id: AND-CONTRACTOR-003
title: "Contractor capture"
stage: 8
surface: android
role: contractor
priority: P0
fr: ["FR-06", "FR-07", "FR-08"]
route: "CaptureScreen (contractor mode)"
suggested_target: "mobile/lib/features/capture/"
api: ["POST /evidence/upload-url", "POST /evidence"]
links_to: []
states: ["default", "camera-contractor-evidence", "after-the-shot-saved-waiting-to-upload", "loading", "error"]
inventory_refs: ["CO-06"]
missing_endpoints: []
source_boards: ["Con-Android.dc.html"]
---

# AND-CONTRACTOR-003 · Contractor capture

## 1. Purpose

In-app camera for contractor evidence, clearly labelled as not counting toward verification, then saved and waiting to upload.

From the approved board (`Con-Android.dc.html`): "The same app as the supervisor's, with the contractor's role: see projects, claim a milestone on site, take contractor photos, follow orders and alerts. Uses the Stage 2 Android kit: 48dp targets, flat surfaces, in-app camera only. Every contractor photo is labelled as contractor evidence from shutter to gallery."

Stage 1 inventory: CO-06. Priority P0 · FRs FR-06, FR-07, FR-08.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Camera · contractor evidence | android | 360×800 | [android.png](android.png) |
| 2 | After the shot · saved, waiting to upload | android | 360×800 | [android-02-after-the-shot-saved-waiting-to-uplo.png](android-02-after-the-shot-saved-waiting-to-uplo.png) |

Components (see [components.md](../../../01-design-system/components.md)): Buttons, Camera and capture bar, Card.

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

Actions on the design: "Retake", "Use photo".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /evidence/upload-url`
- `POST /evidence`

## 5. States and error cases

Designed states: Camera · contractor evidence; After the shot · saved, waiting to upload.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.
- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.

## 7. Responsive and accessibility notes

- Designed variants: android (2).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
