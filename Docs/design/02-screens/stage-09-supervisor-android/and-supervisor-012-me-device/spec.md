---
id: AND-SUPERVISOR-012
title: "Me, device and system states"
stage: 9
surface: android
role: supervisor
priority: P0
fr: ["FR-02", "FR-07"]
route: "MeScreen"
suggested_target: "mobile/lib/features/auth/ (profile)"
api: ["GET /supervisors/me/profile", "POST /devices/{id}/revoke"]
links_to: []
states: ["default", "me-profile-vetting-device", "storage-low", "session-expired", "loading", "error"]
inventory_refs: ["NS-08", "NS-10"]
missing_endpoints: ["MX-12"]
source_boards: ["Sup-Profile.dc.html"]
---

# AND-SUPERVISOR-012 · Me, device and system states

## 1. Purpose

Supervisor profile, vetting, the registered device, storage low and session expired.

From the approved board (`Sup-Profile.dc.html`): "His account: vetting status, the one registered phone that signs his captures, and the rotation notice. Two system states protect unsent evidence: low storage (nothing waiting to upload is ever deleted) and an expired session (captures wait safely until he signs in again on the same phone)."

Stage 1 inventory: NS-08, NS-10. Priority P0 · FRs FR-02, FR-07.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Me · profile, vetting, device | android | 360×800 | [android.png](android.png) |
| 2 | Storage low | android | 360×800 | [android-02-storage-low.png](android-02-storage-low.png) |
| 3 | Session expired | android | 360×800 | [android-03-session-expired.png](android-03-session-expired.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Android app bar and bottom nav, Buttons, Status chip, Alert and banner, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Vetting status | vetting_status: pending \| approved \| rejected, rejection_reason |
| Device | devices.device_id, registered_at, revoked_at (list: see MX-12) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Sign out", "Upload now", "Clear uploaded copies", "Sign in with phone number".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /supervisors/me/profile`
- `POST /devices/{id}/revoke`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-12: List my devices

## 5. States and error cases

Designed states: Me · profile, vetting, device; Storage low; Session expired.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.

## 7. Responsive and accessibility notes

- Designed variants: android (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[3 days]`, `[30 days]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-12: GET the signed-in user's registered devices. The Spec has register and revoke only.
