---
id: WEB-OPS-013
title: "Ops profile, alerts and security"
stage: 12
surface: web
role: ops
priority: P1
fr: ["FR-20"]
route: "/ops/settings"
suggested_target: "web/src/features/ops-console/"
api: ["GET /me"]
links_to: []
states: ["default", "ops-profile-alerts-and-security", "loading", "error"]
inventory_refs: ["NS-06", "NS-07"]
missing_endpoints: ["MX-01"]
source_boards: ["X-Settings.dc.html"]
---

# WEB-OPS-013 · Ops profile, alerts and security

## 1. Purpose

Ops alert channels (money alerts cannot be switched off), WAT time zone and session rules.

From the approved board (`X-Settings.dc.html`): "Profile, time zone, currency, notification channels, devices and data and privacy for client, contractor, supervisor, supplier and ops. Revoking a device is the one destructive action here, so it gets a red button inside a dialog."

Stage 1 inventory: NS-06, NS-07. Priority P1 · FRs FR-20.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Ops · profile, alerts and security | desktop | 1280×800 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Toggle, checkbox and radio card, Table, Card, Avatar (initials).

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Security", "Data and privacy".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /me`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-01: Update own profile and preferences

## 5. States and error cases

Designed states: Ops · profile, alerts and security.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- Every money movement and sensitive action is audit-logged; the audit log is read-only.

Designer note on the board (`X-Settings.dc.html`), **Settings, the same everywhere**:

> Each role gets the same five sections, keeping only what applies: profile, time zone and currency, notifications, devices and sessions, data and privacy.
> Some messages can't be fully switched off: approvals and disputes for clients, spot-check SMS for supervisors, money alerts for ops.
> Time zone: clients pick theirs. Contractors, suppliers, supervisors and ops are fixed to Enugu (WAT).
> Currency: only clients choose (GBP, USD or EUR). Everyone else sees naira.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Session length is PLACEHOLDER ([8 hours] / [30 minutes] idle).
- PLACEHOLDER values on this screen (in square brackets on the design): `[8 hours]`, `[30 minutes]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-01: Name, country, time zone, consent, notification channel order, quiet hours. The Spec has only GET /me.
