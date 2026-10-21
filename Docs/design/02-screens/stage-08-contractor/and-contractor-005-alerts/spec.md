---
id: AND-CONTRACTOR-005
title: "Alerts (Android)"
stage: 8
surface: android
role: contractor
priority: P1
fr: ["FR-20"]
route: "AlertsScreen"
suggested_target: "mobile/lib/features/notifications/ (new folder; not in the Spec)"
api: []
links_to: []
states: ["default", "alerts-wed-6-jan", "loading", "error"]
inventory_refs: ["NS-04"]
missing_endpoints: ["MX-11"]
source_boards: ["Con-Android.dc.html"]
---

# AND-CONTRACTOR-005 · Alerts (Android)

## 1. Purpose

In-app alerts for the contractor (verified, rejected, released, dispute updates).

From the approved board (`Con-Android.dc.html`): "The same app as the supervisor's, with the contractor's role: see projects, claim a milestone on site, take contractor photos, follow orders and alerts. Uses the Stage 2 Android kit: 48dp targets, flat surfaces, in-app camera only. Every contractor photo is labelled as contractor evidence from shutter to gallery."

Stage 1 inventory: NS-04. Priority P1 · FRs FR-20.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Alerts · Wed 6 Jan | android | 360×800 | [android.png](android.png) |

Components (see [components.md](../../../01-design-system/components.md)): Contractor app bottom nav, Status chip.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Notification rows | notifications.template, payload, channel, sent_at: see MX-11 |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-11: In-app notification feed

## 5. States and error cases

Designed states: Alerts · Wed 6 Jan.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Role and project membership decide what is visible (Spec, two-layer authorisation).

## 7. Responsive and accessibility notes

- Designed variants: android (1).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-11: List the signed-in user's notifications and mark them read (notifications table exists, no endpoint).
