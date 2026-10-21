---
id: WEB-CLIENT-002
title: "Session expired (mobile web)"
stage: 4
surface: mobile-web
role: client
priority: P0
fr: ["FR-01"]
route: "(overlay on any client route)"
suggested_target: "web/src/common/ (auth)"
api: ["POST /auth/refresh", "POST /auth/otp/request", "POST /auth/otp/verify"]
links_to: []
states: ["default", "session-expired-mobile-web-bottom-sheet", "loading", "error"]
inventory_refs: ["NS-10"]
missing_endpoints: []
source_boards: ["Auth-OpsSession.dc.html"]
---

# WEB-CLIENT-002 · Session expired (mobile web)

## 1. Purpose

Bottom sheet asking a client to sign in again without losing their place.

From the approved board (`Auth-OpsSession.dc.html`): "Ops uses the same one-time codes, by work email only, and lands on the work queue. Sessions refresh quietly in the background; when the long session ends we explain why and return people to where they were."

Stage 1 inventory: NS-10. Priority P0 · FRs FR-01.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Session expired · mobile web (bottom sheet) | mobile | 390×844 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Buttons, Dialog and alert dialog, Bottom sheet and side panel.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Send me a code", "Not now".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /auth/refresh`
- `POST /auth/otp/request`
- `POST /auth/otp/verify`

## 5. States and error cases

Designed states: Session expired · mobile web (bottom sheet).

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.

## 7. Responsive and accessibility notes

- Designed variants: mobile (1).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Client session length is PLACEHOLDER ([12 hours]).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
