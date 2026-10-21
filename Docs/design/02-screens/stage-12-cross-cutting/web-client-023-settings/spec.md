---
id: WEB-CLIENT-023
title: "Client settings"
stage: 12
surface: web
role: client
priority: P1
fr: ["FR-20", "FR-01"]
route: "/settings"
suggested_target: "web/src/features/settings/ (new folder; not in the Spec)"
api: ["GET /me"]
links_to: []
states: ["default", "client-notifications", "client-time-zone-and-currency", "client-data-and-privacy", "loading", "error"]
inventory_refs: ["NS-07", "NS-09"]
missing_endpoints: ["MX-01", "MX-19"]
source_boards: ["X-Settings.dc.html"]
---

# WEB-CLIENT-023 · Client settings

## 1. Purpose

Notification channel order and events, time zone and currency, data and privacy.

From the approved board (`X-Settings.dc.html`): "Profile, time zone, currency, notification channels, devices and data and privacy for client, contractor, supervisor, supplier and ops. Revoking a device is the one destructive action here, so it gets a red button inside a dialog."

Stage 1 inventory: NS-07, NS-09. Priority P1 · FRs FR-20, FR-01.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Client · notifications | desktop | 1280×800 | [desktop.png](desktop.png) |
| 2 | Client · time zone and currency | desktop | 1280×800 | [desktop-02-client-time-zone-and-currency.png](desktop-02-client-time-zone-and-currency.png) |
| 3 | Client · data and privacy | desktop | 1280×800 | [desktop-03-client-data-and-privacy.png](desktop-03-client-data-and-privacy.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Buttons, Text input and select, Toggle, checkbox and radio card, Status chip, Money display, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Signed-in user | GET /me -> full_name, role, timezone, country, phone, email |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Time zone and currency", "Devices and sessions", "Data and privacy", "Save changes", "Cancel", "Request download", "Delete account".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /me`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-01: Update own profile and preferences
- MX-19: Sign out and sessions

## 5. States and error cases

Designed states: Client · notifications; Client · time zone and currency; Client · data and privacy.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.

Designer note on the board (`X-Settings.dc.html`), **Settings, the same everywhere**:

> Each role gets the same five sections, keeping only what applies: profile, time zone and currency, notifications, devices and sessions, data and privacy.
> Some messages can't be fully switched off: approvals and disputes for clients, spot-check SMS for supervisors, money alerts for ops.
> Time zone: clients pick theirs. Contractors, suppliers, supervisors and ops are fixed to Enugu (WAT).
> Currency: only clients choose (GBP, USD or EUR). Everyone else sees naira.

## 7. Responsive and accessibility notes

- Designed variants: desktop (3).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Quiet hours are a design addition, not in the Spec.
- PLACEHOLDER values on this screen (in square brackets on the design): `[24 hours]`, `[7 years]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-01: Name, country, time zone, consent, notification channel order, quiet hours. The Spec has only GET /me.
- MX-19: Revoke the refresh token on sign-out and list or end active sessions. No endpoint in the Spec.
