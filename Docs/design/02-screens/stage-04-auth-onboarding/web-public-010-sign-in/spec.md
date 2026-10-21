---
id: WEB-PUBLIC-010
title: "Sign in or sign up"
stage: 4
surface: web
role: public
priority: P0
fr: ["FR-01"]
route: "/sign-in"
suggested_target: "web/src/features/auth/"
api: ["POST /auth/otp/request", "POST /auth/otp/verify", "GET /me"]
links_to: ["WEB-PUBLIC-001", "WEB-PUBLIC-007", "WEB-PUBLIC-008", "WEB-PUBLIC-009"]
states: ["default", "enter-phone", "enter-phone", "code", "country-selector-search-common-countries-first", "email-code-by-email-only", "code-entry-5-minute-countdown-resend-after-30-s", "wrong-code-attempts-left-shown", "too-many-attempts-code-cancelled", "code-expired-after-5-minutes", "rate-limited-per-number-and-device", "channel-unavailable-server-503", "send-failed-server-502", "consent-first-sign-up-ndpa-2023", "loading", "error"]
inventory_refs: ["AU-01", "AU-02"]
missing_endpoints: []
source_boards: ["Auth-SignIn.dc.html"]
---

# WEB-PUBLIC-010 · Sign in or sign up

## 1. Purpose

One-time-code sign-in for every role on the web: phone (WhatsApp or SMS) or email, then the 6-digit code.

From the approved board (`Auth-SignIn.dc.html`): "Phone or email 6-digit code Consent (new accounts) Role onboarding Home"

Stage 1 inventory: AU-01, AU-02. Priority P0 · FRs FR-01.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Enter phone | desktop | 1280×800 | [desktop.png](desktop.png) |
| 2 | Enter phone | mobile | 390×844 | [mobile.png](mobile.png) |
| 3 | Code | mobile | 390×844 | [mobile-02-code.png](mobile-02-code.png) |
| 4 | Country selector Search, common countries first | card | 480×896 | [card.png](card.png) |
| 5 | Email Code by email only | card | 480×476 | [card-02-email-code-by-email-only.png](card-02-email-code-by-email-only.png) |
| 6 | Code entry 5-minute countdown, resend after 30 s | card | 480×480 | [card-03-code-entry-5-minute-countdown-resend.png](card-03-code-entry-5-minute-countdown-resend.png) |
| 7 | Wrong code Attempts left shown | card | 480×568 | [card-04-wrong-code-attempts-left-shown.png](card-04-wrong-code-attempts-left-shown.png) |
| 8 | Too many attempts Code cancelled | card | 480×568 | [card-05-too-many-attempts-code-cancelled.png](card-05-too-many-attempts-code-cancelled.png) |
| 9 | Code expired After 5 minutes | card | 480×568 | [card-06-code-expired-after-5-minutes.png](card-06-code-expired-after-5-minutes.png) |
| 10 | Rate limited Per number and device | card | 480×642 | [card-07-rate-limited-per-number-and-device.png](card-07-rate-limited-per-number-and-device.png) |
| 11 | Channel unavailable Server: 503 | card | 480×621 | [card-08-channel-unavailable-server-503.png](card-08-channel-unavailable-server-503.png) |
| 12 | Send failed Server: 502 | card | 480×621 | [card-09-send-failed-server-502.png](card-09-send-failed-server-502.png) |
| 13 | Consent — first sign-up NDPA 2023 | card | 480×750 | [card-10-consent-first-sign-up-ndpa-2023.png](card-10-consent-first-sign-up-ndpa-2023.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Buttons, Text input and select, OTP code input, Segmented control and tabs, Escrow trust line, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Phone or email | POST /auth/otp/request {identifier, channel} |
| 6-digit code | POST /auth/otp/verify {identifier, code} -> access + refresh tokens |
| Countdown | otp expires in 5 minutes; resend after 30 s (design assumption) |
| Signed-in user | GET /me -> full_name, role, timezone, country, phone, email |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Phone", "Email", "Send code", "Back", "Verify", "Send a new code", "Try again in 9:41", "Try again", "Agree and continue".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /auth/otp/request`
- `POST /auth/otp/verify`
- `GET /me`

Navigates to: WEB-PUBLIC-001, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009.

## 5. States and error cases

Designed states: Enter phone; Enter phone; Code; Country selector Search, common countries first; Email Code by email only; Code entry 5-minute countdown, resend after 30 s; Wrong code Attempts left shown; Too many attempts Code cancelled; Code expired After 5 minutes; Rate limited Per number and device; Channel unavailable Server: 503; Send failed Server: 502; Consent — first sign-up NDPA 2023.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `notifications_not_configured`, `notification_failed`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.
- Role and project membership are checked on every request; each role sees only its own screens.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (2), card (10).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Resend unlock after 30 s is a design assumption (Stage 1, confirmed).
- No error codes are defined for wrong, expired or too many codes; see error-codes-to-ui.md.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
