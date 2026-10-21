---
id: AND-SUPERVISOR-015
title: "Supervisor settings and revoke"
stage: 12
surface: android
role: supervisor
priority: P0
fr: ["FR-07", "FR-20"]
route: "SettingsScreen"
suggested_target: "mobile/lib/features/auth/ (settings)"
api: ["POST /devices/{id}/revoke"]
links_to: []
states: ["default", "supervisor-app-settings", "supervisor-app-revoke-old-phone", "loading", "error"]
inventory_refs: ["NS-07", "NS-08"]
missing_endpoints: ["MX-01", "MX-12"]
source_boards: ["X-Settings.dc.html"]
---

# AND-SUPERVISOR-015 · Supervisor settings and revoke

## 1. Purpose

Supervisor app settings and revoking an old phone.

From the approved board (`X-Settings.dc.html`): "Profile, time zone, currency, notification channels, devices and data and privacy for client, contractor, supervisor, supplier and ops. Revoking a device is the one destructive action here, so it gets a red button inside a dialog."

Stage 1 inventory: NS-07, NS-08. Priority P0 · FRs FR-07, FR-20.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Supervisor app · settings | android | 360×800 | [android.png](android.png) |
| 2 | Supervisor app · revoke old phone | android | 360×800 | [android-02-supervisor-app-revoke-old-phone.png](android-02-supervisor-app-revoke-old-phone.png) |

Components (see [components.md](../../../01-design-system/components.md)): Android app bar and bottom nav, Buttons, Toggle, checkbox and radio card, Status chip, Dialog and alert dialog, Bottom sheet and side panel, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Device | devices.device_id, registered_at, revoked_at (list: see MX-12) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Revoke", "Revoke device", "Cancel".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /devices/{id}/revoke`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-01: Update own profile and preferences
- MX-12: List my devices

## 5. States and error cases

Designed states: Supervisor app · settings; Supervisor app · revoke old phone.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.

Designer note on the board (`X-Settings.dc.html`), **Settings, the same everywhere**:

> Each role gets the same five sections, keeping only what applies: profile, time zone and currency, notifications, devices and sessions, data and privacy.
> Some messages can't be fully switched off: approvals and disputes for clients, spot-check SMS for supervisors, money alerts for ops.
> Time zone: clients pick theirs. Contractors, suppliers, supervisors and ops are fixed to Enugu (WAT).
> Currency: only clients choose (GBP, USD or EUR). Everyone else sees naira.

## 7. Responsive and accessibility notes

- Designed variants: android (2).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-01: Name, country, time zone, consent, notification channel order, quiet hours. The Spec has only GET /me.
- MX-12: GET the signed-in user's registered devices. The Spec has register and revoke only.
