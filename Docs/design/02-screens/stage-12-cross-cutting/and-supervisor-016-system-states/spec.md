---
id: AND-SUPERVISOR-016
title: "System states (Android)"
stage: 12
surface: android
role: supervisor
priority: P0
fr: ["FR-01", "FR-06"]
route: "(shared app states)"
suggested_target: "mobile/lib/core/ (UI kit)"
api: []
links_to: []
states: ["default", "server-error", "location-permission-denied", "camera-permission-denied", "not-allowed-rotated-off", "form-validation", "loading-skeleton", "snackbars", "confirmation-dialog", "destructive-dialog", "loading", "error"]
inventory_refs: ["NS-10"]
missing_endpoints: []
source_boards: ["X-StatesAndroid.dc.html"]
---

# AND-SUPERVISOR-016 · System states (Android)

## 1. Purpose

Server error, location and camera permission denied, not allowed (rotated off), validation, skeleton, snackbars and dialogs in the app.

From the approved board (`X-StatesAndroid.dc.html`): "The same patterns for the supervisor and contractor app. Offline, sync conflict (409) and session expiry are already designed in Stage 9 and reused as is. These add server errors, phone permissions, role and rotation limits, validation, skeletons, snackbars and both kinds of dialog."

Stage 1 inventory: NS-10. Priority P0 · FRs FR-01, FR-06.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Server error | android | 360×800 | [android.png](android.png) |
| 2 | Location permission denied | android | 360×800 | [android-02-location-permission-denied.png](android-02-location-permission-denied.png) |
| 3 | Camera permission denied | android | 360×800 | [android-03-camera-permission-denied.png](android-03-camera-permission-denied.png) |
| 4 | Not allowed · rotated off | android | 360×800 | [android-04-not-allowed-rotated-off.png](android-04-not-allowed-rotated-off.png) |
| 5 | Form validation | android | 360×800 | [android-05-form-validation.png](android-05-form-validation.png) |
| 6 | Loading skeleton | android | 360×800 | [android-06-loading-skeleton.png](android-06-loading-skeleton.png) |
| 7 | Snackbars | android | 360×800 | [android-07-snackbars.png](android-07-snackbars.png) |
| 8 | Confirmation dialog | android | 360×800 | [android-08-confirmation-dialog.png](android-08-confirmation-dialog.png) |
| 9 | Destructive dialog | android | 360×800 | [android-09-destructive-dialog.png](android-09-destructive-dialog.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Android app bar and bottom nav, Buttons, Text input and select, Alert and banner, Toast and snackbar, Skeleton loader, Error page, Dialog and alert dialog, Bottom sheet and side panel, Evidence card, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Try again", "Open sync queue", "Open phone settings", "Not now", "Back to my projects", "Send back to Engr. Obi", "Submit findings", "Keep editing", "Delete capture", "Keep it".

## 5. States and error cases

Designed states: Server error; Location permission denied; Camera permission denied; Not allowed · rotated off; Form validation; Loading skeleton; Snackbars; Confirmation dialog; Destructive dialog.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `conflict_409`.

## 6. Business rules the UI must enforce

- Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- Status colour appears only in chips and alerts, and every state also differs by text or shape.

## 7. Responsive and accessibility notes

- Designed variants: android (9).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
