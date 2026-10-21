---
id: AND-CONTRACTOR-006
title: "Contractor push notifications"
stage: 12
surface: android
role: contractor
priority: P1
fr: ["FR-20"]
route: "push templates"
suggested_target: "mobile/lib/core/ (FCM)"
api: []
links_to: []
states: ["default", "contractor-app-notifications", "loading", "error"]
inventory_refs: ["NS-04"]
missing_endpoints: []
source_boards: ["X-Push.dc.html"]
---

# AND-CONTRACTOR-006 · Contractor push notifications

## 1. Purpose

Push notifications for verified, sent back, released and dispute updates.

From the approved board (`X-Push.dc.html`): "Android push for the two app roles, as they appear on the lock screen."

Stage 1 inventory: NS-04. Priority P1 · FRs FR-20.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Contractor app · notifications | android | 360×800 | [android.png](android.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Escrow trust line, Push and SMS notification, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

## 5. States and error cases

Designed states: Contractor app · notifications.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."

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

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
