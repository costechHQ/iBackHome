---
id: WEB-CLIENT-001
title: "Client onboarding"
stage: 4
surface: web
role: client
priority: P0
fr: ["FR-01"]
route: "/welcome"
suggested_target: "web/src/features/auth/"
api: ["GET /me"]
links_to: []
states: ["default", "step-1-of-3-your-details", "step-2-of-3-location-and-currency", "step-3-of-3-notifications", "empty-dashboard", "step-2", "empty-dashboard", "loading", "error"]
inventory_refs: ["AU-04"]
missing_endpoints: ["MX-01"]
source_boards: ["Onboard-Client.dc.html"]
---

# WEB-CLIENT-001 · Client onboarding

## 1. Purpose

First-time profile for a client: details, location, time zone and currency, notification channels, consent, then the empty dashboard.

From the approved board (`Onboard-Client.dc.html`): "Three short steps after consent, then an empty dashboard with one clear action. Everything here can be changed later in Settings."

Stage 1 inventory: AU-04. Priority P0 · FRs FR-01.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Step 1 of 3 — Your details | desktop | 1280×800 | [desktop.png](desktop.png) |
| 2 | Step 2 of 3 — Location and currency | desktop | 1280×800 | [desktop-02-step-2-of-3-location-and-currency.png](desktop-02-step-2-of-3-location-and-currency.png) |
| 3 | Step 3 of 3 — Notifications | desktop | 1280×800 | [desktop-03-step-3-of-3-notifications.png](desktop-03-step-3-of-3-notifications.png) |
| 4 | Empty dashboard | desktop | 1280×800 | [desktop-04-empty-dashboard.png](desktop-04-empty-dashboard.png) |
| 5 | Step 2 | mobile | 390×844 | [mobile.png](mobile.png) |
| 6 | Empty dashboard | mobile | 390×700 | [mobile-02-empty-dashboard.png](mobile-02-empty-dashboard.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Buttons, Text input and select, Status chip, Empty state, Escrow trust line, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Signed-in user | GET /me -> full_name, role, timezone, country, phone, email |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Back", "Continue", "Finish", "Create your first project".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /me`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-01: Update own profile and preferences

## 5. States and error cases

Designed states: Step 1 of 3 — Your details; Step 2 of 3 — Location and currency; Step 3 of 3 — Notifications; Empty dashboard; Step 2; Empty dashboard.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.

## 7. Responsive and accessibility notes

- Designed variants: desktop (4), mobile (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Consent wording is PLACEHOLDER pending legal review (NDPA).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-01: Name, country, time zone, consent, notification channel order, quiet hours. The Spec has only GET /me.
