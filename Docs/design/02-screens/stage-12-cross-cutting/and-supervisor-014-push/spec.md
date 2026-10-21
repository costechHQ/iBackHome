---
id: AND-SUPERVISOR-014
title: "Supervisor push notifications"
stage: 12
surface: android
role: supervisor
priority: P1
fr: ["FR-20"]
route: "push templates"
suggested_target: "mobile/lib/core/ (FCM) "
api: []
links_to: []
states: ["default", "supervisor-app-notifications", "loading", "error"]
inventory_refs: ["NS-05"]
missing_endpoints: []
source_boards: ["X-Push.dc.html"]
---

# AND-SUPERVISOR-014 · Supervisor push notifications

## 1. Purpose

Push notifications for claims to verify, flags, spot checks, uploads due and reports to review.

From the approved board (`X-Push.dc.html`): "Android push for the two app roles, as they appear on the lock screen."

Stage 1 inventory: NS-05. Priority P1 · FRs FR-20.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Supervisor app · notifications | android | 360×800 | [android.png](android.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Evidence card, Push and SMS notification, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

## 5. States and error cases

Designed states: Supervisor app · notifications.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Spot checks are unannounced: the contractor is never notified; the client sees results only after ops closes them.
- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.

Designer note on the board (`X-Push.dc.html`), **Push rules**:

> Push goes only to the Android app (supervisors and contractors). Clients and suppliers get WhatsApp and email.
> Lock-screen text never shows client names for spot checks, amounts for supervisors, or anything a stranger shouldn't read. People can hide all previews in Settings.
> Every push opens the exact screen it's about. Sync and capture alerts can't be switched off.

## 7. Responsive and accessibility notes

- Designed variants: android (1).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- DECIDED 2026-10-21 (C-1): the Spec wins. The upload window is 72 h with a warning at 48 h; the push copy now says "Upload within 72 h" (the PNG still shows 48 h). Fill the hours from config.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
