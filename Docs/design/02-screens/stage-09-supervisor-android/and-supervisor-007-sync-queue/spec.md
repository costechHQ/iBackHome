---
id: AND-SUPERVISOR-007
title: "Sync queue"
stage: 9
surface: android
role: supervisor
priority: P0
fr: ["FR-09", "FR-08", "FR-10"]
route: "SyncScreen"
suggested_target: "mobile/lib/features/sync/"
api: ["POST /evidence/upload-url", "POST /evidence"]
links_to: []
states: ["default", "sync-queue-online-wed-6-jan-15-45", "offline-48-hour-warning-fri-8-jan-08-10", "retry-states", "rejected-capture-reason", "loading", "error"]
inventory_refs: ["SV-05", "SV-06", "SV-10"]
missing_endpoints: []
source_boards: ["Sup-Sync.dc.html"]
---

# AND-SUPERVISOR-007 · Sync queue

## 1. Purpose

Offline queue: queued, uploading, accepted, flagged, rejected with reason; 48-hour warning; retry states.

From the approved board (`Sup-Sync.dc.html`): "Every capture and decision waits in a queue on the phone until the server accepts it. Each item shows one status: queued, uploading, accepted, flagged or rejected, and a rejection always says why. The offline banner, the 48-hour warning and the retry states keep him from leaving site with evidence that won't count."

Stage 1 inventory: SV-05, SV-06, SV-10. Priority P0 · FRs FR-09, FR-08, FR-10.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Sync queue · online · Wed 6 Jan, 15:45 | android | 360×800 | [android.png](android.png) |
| 2 | Offline · 48-hour warning · Fri 8 Jan, 08:10 | android | 360×800 | [android-02-offline-48-hour-warning-fri-8-jan-08.png](android-02-offline-48-hour-warning-fri-8-jan-08.png) |
| 3 | Retry states | android | 360×800 | [android-03-retry-states.png](android-03-retry-states.png) |
| 4 | Rejected capture · reason | android | 360×800 | [android-04-rejected-capture-reason.png](android-04-rejected-capture-reason.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Android app bar and bottom nav, Buttons, Status chip, Alert and banner, Evidence card, Three-checks list, Checklist row, Sync row, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Status chip | evidence.status: pending_checks \| accepted \| flagged \| rejected |
| Three checks | per-check results (inside the site geofence, device-signed, not reused): see MX-07; until then derive from status + reject_reason |
| GPS point and accuracy | latitude, longitude, accuracy_m |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Retry now", "Retry all now", "Retake now".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /evidence/upload-url`
- `POST /evidence`

## 5. States and error cases

Designed states: Sync queue · online · Wed 6 Jan, 15:45; Offline · 48-hour warning · Fri 8 Jan, 08:10; Retry states; Rejected capture · reason.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- A flagged item goes to ops and never rejects a milestone by itself.
- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.

## 7. Responsive and accessibility notes

- Designed variants: android (4).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- DECIDED 2026-10-21 (C-1): the Spec wins. Captures not uploaded within 72 h are rejected and the app warns at 48 h; the offline banner copy now says 72 hours (the PNG still shows 48 hours). Fill the hours from config.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
