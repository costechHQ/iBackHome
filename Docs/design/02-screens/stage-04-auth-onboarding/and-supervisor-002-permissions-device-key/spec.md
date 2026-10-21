---
id: AND-SUPERVISOR-002
title: "Permissions and capture key"
stage: 4
surface: android
role: supervisor
priority: P0
fr: ["FR-06", "FR-07"]
route: "PermissionsScreen, DeviceKeyScreen"
suggested_target: "mobile/lib/core/ (signing keys) + mobile/lib/features/auth/"
api: ["POST /devices"]
links_to: []
states: ["default", "10-permissions", "11-secure-capture-key", "12-key-ready", "loading", "error"]
inventory_refs: ["AU-06"]
missing_endpoints: []
source_boards: ["Onboard-Supervisor.dc.html"]
---

# AND-SUPERVISOR-002 · Permissions and capture key

## 1. Purpose

Ask for camera and location permission, generate the ECDSA P-256 key in the Android Keystore and register its public key.

From the approved board (`Onboard-Supervisor.dc.html`): "From "Apply" on the public site, the supervisor signs in with a code in the app, completes five steps, and waits for ops. After approval: permissions, then the secure capture key that signs every photo. No site can be assigned until vetting is approved."

Stage 1 inventory: AU-06. Priority P0 · FRs FR-06, FR-07.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | 10 · Permissions | android | 360×800 | [android.png](android.png) |
| 2 | 11 · Secure capture key | android | 360×800 | [android-02-11-secure-capture-key.png](android-02-11-secure-capture-key.png) |
| 3 | 12 · Key ready | android | 360×800 | [android-03-12-key-ready.png](android-03-12-key-ready.png) |

Components (see [components.md](../../../01-design-system/components.md)): Buttons, Status chip, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Device | devices.device_id, registered_at, revoked_at (list: see MX-12) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Allow", "Create my capture key", "Go to my sites".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /devices`

## 5. States and error cases

Designed states: 10 · Permissions; 11 · Secure capture key; 12 · Key ready.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.

## 7. Responsive and accessibility notes

- Designed variants: android (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
