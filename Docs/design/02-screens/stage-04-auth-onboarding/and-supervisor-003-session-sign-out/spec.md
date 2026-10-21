---
id: AND-SUPERVISOR-003
title: "Session expired and sign out (Android)"
stage: 4
surface: android
role: supervisor
priority: P0
fr: ["FR-01", "FR-09"]
route: "SessionExpiredSheet, SignOutDialog"
suggested_target: "mobile/lib/features/auth/"
api: ["POST /auth/refresh", "POST /auth/otp/request", "POST /auth/otp/verify"]
links_to: []
states: ["default", "session-expired-android-queue-is-safe", "sign-out-android-with-unsent-captures", "loading", "error"]
inventory_refs: ["NS-10"]
missing_endpoints: ["MX-19"]
source_boards: ["Auth-OpsSession.dc.html"]
---

# AND-SUPERVISOR-003 · Session expired and sign out (Android)

## 1. Purpose

Tell a supervisor their queued captures are safe when the session expires, and warn before signing out with unsent captures.

From the approved board (`Auth-OpsSession.dc.html`): "Ops uses the same one-time codes, by work email only, and lands on the work queue. Sessions refresh quietly in the background; when the long session ends we explain why and return people to where they were."

Stage 1 inventory: NS-10. Priority P0 · FRs FR-01, FR-09.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Session expired · Android (queue is safe) | android | 360×800 | [android.png](android.png) |
| 2 | Sign out · Android (with unsent captures) | android | 360×800 | [android-02-sign-out-android-with-unsent-capture.png](android-02-sign-out-android-with-unsent-capture.png) |

Components (see [components.md](../../../01-design-system/components.md)): Buttons, Dialog and alert dialog, Sync row, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Upload first", "Sign out anyway".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /auth/refresh`
- `POST /auth/otp/request`
- `POST /auth/otp/verify`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-19: Sign out and sessions

## 5. States and error cases

Designed states: Session expired · Android (queue is safe); Sign out · Android (with unsent captures).

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.

## 7. Responsive and accessibility notes

- Designed variants: android (2).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-19: Revoke the refresh token on sign-out and list or end active sessions. No endpoint in the Spec.
