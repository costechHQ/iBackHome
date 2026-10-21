---
id: AND-SUPERVISOR-013
title: "Spot check SMS and push"
stage: 12
surface: android
role: supervisor
priority: P1
fr: ["FR-20", "FR-11"]
route: "push + SMS: spot_check_assigned"
suggested_target: "backend/app/base/notifications/ + mobile push handling"
api: []
links_to: []
states: ["default", "supervisor-sms-push-spot-check-assigned", "loading", "error"]
inventory_refs: ["NS-05"]
missing_endpoints: []
source_boards: ["X-Messages.dc.html"]
---

# AND-SUPERVISOR-013 · Spot check SMS and push

## 1. Purpose

Spot check assigned by push and SMS, leaving out the client's name and exact address.

From the approved board (`X-Messages.dc.html`): "The five events from the notification table, as people actually receive them. The client gets WhatsApp. The spot check goes to the supervisor by push and SMS, because the spec routes it that way. Shown in a neutral chat layout, not WhatsApp's own branding."

Stage 1 inventory: NS-05. Priority P1 · FRs FR-20, FR-11.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Supervisor · SMS + push · spot check assigned | android | 360×800 | [android.png](android.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Push and SMS notification, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

## 5. States and error cases

Designed states: Supervisor · SMS + push · spot check assigned.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Spot checks are unannounced: the contractor is never notified; the client sees results only after ops closes them.

Designer note on the board (`X-Messages.dc.html`), **Message rules**:

> Every message says what happened, the money in both currencies when relevant, and one clear button.
> Messages sent outside WhatsApp's 24-hour window use Meta-approved templates. Each event above is one template.
> Never in a message: login codes (sent only on the channel asked for), full bank numbers, or another party's phone number.
> If WhatsApp fails, the same message goes by push, then SMS, then email, in the person's preferred order.

## 7. Responsive and accessibility notes

- Designed variants: android (1).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
