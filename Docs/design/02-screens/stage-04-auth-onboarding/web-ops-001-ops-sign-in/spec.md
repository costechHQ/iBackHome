---
id: WEB-OPS-001
title: "Ops sign-in and session"
stage: 4
surface: web
role: ops
priority: P0
fr: ["FR-01", "FR-19"]
route: "/ops/sign-in"
suggested_target: "web/src/features/ops-console/"
api: ["POST /auth/otp/request", "POST /auth/otp/verify", "POST /auth/refresh", "GET /me", "GET /ops/queue"]
links_to: ["WEB-PUBLIC-001", "WEB-PUBLIC-010"]
states: ["default", "ops-sign-in-desktop-only", "ops-landing-work-queue", "session-expired-desktop-return-to-the-same-page", "signed-out-desktop", "loading", "error"]
inventory_refs: ["AU-01", "AU-02", "NS-10"]
missing_endpoints: ["MX-19"]
source_boards: ["Auth-OpsSession.dc.html"]
---

# WEB-OPS-001 · Ops sign-in and session

## 1. Purpose

Desktop-only ops sign-in, landing on the work queue, session expired (return to the same page) and signed out.

From the approved board (`Auth-OpsSession.dc.html`): "Ops uses the same one-time codes, by work email only, and lands on the work queue. Sessions refresh quietly in the background; when the long session ends we explain why and return people to where they were."

Stage 1 inventory: AU-01, AU-02, NS-10. Priority P0 · FRs FR-01, FR-19.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Ops · sign-in (desktop only) | desktop | 1280×800 | [desktop.png](desktop.png) |
| 2 | Ops · landing — work queue | desktop | 1280×800 | [desktop-02-ops-landing-work-queue.png](desktop-02-ops-landing-work-queue.png) |
| 3 | Session expired · desktop (return to the same page) | desktop | 1280×800 | [desktop-03-session-expired-desktop-return-to-th.png](desktop-03-session-expired-desktop-return-to-th.png) |
| 4 | Signed out · desktop | desktop | 1280×800 | [desktop-04-signed-out-desktop.png](desktop-04-signed-out-desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Buttons, Text input and select, Status chip, Dialog and alert dialog, Evidence card, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Phone or email | POST /auth/otp/request {identifier, channel} |
| 6-digit code | POST /auth/otp/verify {identifier, code} -> access + refresh tokens |
| Countdown | otp expires in 5 minutes; resend after 30 s (design assumption) |
| Queue counts and items | GET /ops/queue -> vetting, flagged evidence, disputes |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Email me a code", "Open", "Not now", "Send me a code", "Sign in again".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /auth/otp/request`
- `POST /auth/otp/verify`
- `POST /auth/refresh`
- `GET /me`
- `GET /ops/queue`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-19: Sign out and sessions

Navigates to: WEB-PUBLIC-001, WEB-PUBLIC-010.

## 5. States and error cases

Designed states: Ops · sign-in (desktop only); Ops · landing — work queue; Session expired · desktop (return to the same page); Signed out · desktop.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `notifications_not_configured`, `notification_failed`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.
- Role and project membership are checked on every request; each role sees only its own screens.

## 7. Responsive and accessibility notes

- Designed variants: desktop (4).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Ops session length is PLACEHOLDER ([8 hours] / [30 minutes] idle).
- Security key for ops is shown in settings but not in the Spec.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-19: Revoke the refresh token on sign-out and list or end active sessions. No endpoint in the Spec.
