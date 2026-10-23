---
id: WEB-CONTRACTOR-010
title: "Devices and revoke"
stage: 12
surface: web
role: contractor
priority: P0
fr: ["FR-07"]
route: "/c/settings/devices"
suggested_target: "web/src/features/settings/ (new folder)"
api: ["POST /devices/{id}/revoke"]
links_to: []
states: ["default", "contractor-devices-revoke", "loading", "error"]
inventory_refs: ["NS-08"]
missing_endpoints: ["MX-12"]
source_boards: ["X-Settings.dc.html"]
---

# WEB-CONTRACTOR-010 · Devices and revoke

## 1. Purpose

Registered capture phones and revoking an old one (its captures stop verifying).

From the approved board (`X-Settings.dc.html`): "Profile, time zone, currency, notification channels, devices and data and privacy for client, contractor, supervisor, supplier and ops. Revoking a device is the one destructive action here, so it gets a red button inside a dialog."

Stage 1 inventory: NS-08. Priority P0 · FRs FR-07.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Contractor · devices · revoke | desktop | 1280×800 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Contractor top bar, Buttons, Status chip, Dialog and alert dialog, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Device | devices.device_id, registered_at, revoked_at (list: see MX-12) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Time zone and currency", "Devices and sessions", "Data and privacy", "Revoke", "Cancel", "Revoke device".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /devices/{id}/revoke`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-12: List my devices

## 5. States and error cases

Designed states: Contractor · devices · revoke.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Every money movement and sensitive action is audit-logged; the audit log is read-only.

Designer note on the board (`X-Settings.dc.html`), **Settings, the same everywhere**:

> Each role gets the same five sections, keeping only what applies: profile, time zone and currency, notifications, devices and sessions, data and privacy.
> Some messages can't be fully switched off: approvals and disputes for clients, spot-check SMS for supervisors, money alerts for ops.
> Time zone: clients pick theirs. Contractors, suppliers, supervisors and ops are fixed to Nigerian time (WAT).
> Currency: only clients choose (GBP, USD or EUR). Everyone else sees naira.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-12: GET the signed-in user's registered devices. The Spec has register and revoke only.
