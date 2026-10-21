---
id: AND-PUBLIC-001
title: "Sign in (Android)"
stage: 4
surface: android
role: public
priority: P0
fr: ["FR-01"]
route: "SignInScreen"
suggested_target: "mobile/lib/features/auth/"
api: ["POST /auth/otp/request", "POST /auth/otp/verify", "GET /me"]
links_to: []
states: ["default", "enter-phone", "code", "loading", "error"]
inventory_refs: ["AU-01", "AU-02"]
missing_endpoints: []
source_boards: ["Auth-SignIn.dc.html"]
---

# AND-PUBLIC-001 · Sign in (Android)

## 1. Purpose

One-time-code sign-in for supervisors and contractors in the Android app.

From the approved board (`Auth-SignIn.dc.html`): "Phone or email 6-digit code Consent (new accounts) Role onboarding Home"

Stage 1 inventory: AU-01, AU-02. Priority P0 · FRs FR-01.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Enter phone | android | 360×800 | [android.png](android.png) |
| 2 | Code | android | 360×800 | [android-02-code.png](android-02-code.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Buttons, Text input and select, OTP code input, Segmented control and tabs.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Phone or email | POST /auth/otp/request {identifier, channel} |
| 6-digit code | POST /auth/otp/verify {identifier, code} -> access + refresh tokens |
| Countdown | otp expires in 5 minutes; resend after 30 s (design assumption) |
| Signed-in user | GET /me -> full_name, role, timezone, country, phone, email |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Phone", "Email", "Send code", "Back", "Verify".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /auth/otp/request`
- `POST /auth/otp/verify`
- `GET /me`

## 5. States and error cases

Designed states: Enter phone; Code.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `notifications_not_configured`, `notification_failed`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.
- Role and project membership are checked on every request; each role sees only its own screens.

## 7. Responsive and accessibility notes

- Designed variants: android (2).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- Tokens stored in Android encrypted storage (Spec).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
