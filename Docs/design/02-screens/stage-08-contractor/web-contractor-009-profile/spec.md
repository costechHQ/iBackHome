---
id: WEB-CONTRACTOR-009
title: "Profile and track record"
stage: 8
surface: web
role: contractor
priority: P1
fr: ["FR-01"]
route: "/c/profile"
suggested_target: "web/src/features/auth/ (profile)"
api: ["GET /me"]
links_to: ["WEB-CONTRACTOR-003", "WEB-CONTRACTOR-007", "WEB-CONTRACTOR-008"]
states: ["default", "desktop", "loading", "error"]
inventory_refs: []
missing_endpoints: ["MX-01", "MX-23"]
source_boards: ["Con-Profile.dc.html"]
---

# WEB-CONTRACTOR-009 · Profile and track record

## 1. Purpose

Contractor profile, checks and a computed track record clients can see.

From the approved board (`Con-Profile.dc.html`): "The facts iBackHome has recorded about his work, which is also what a client sees before inviting him. There are no star ratings or written reviews, only checks and outcomes the platform recorded itself. Wed 6 Jan 2027."

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×920 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Contractor top bar, Status chip, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Edit profile".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /me`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-01: Update own profile and preferences
- MX-23: Contractor public profile and track record

Navigates to: WEB-CONTRACTOR-003, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008.

## 5. States and error cases

Designed states: Desktop.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Not in the Stage 1 inventory; added in Stage 8 from the PRD persona ("public track record"). Priority assumed P1.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-01: Name, country, time zone, consent, notification channel order, quiet hours. The Spec has only GET /me.
- MX-23: Contractor "About" text and computed track record. No endpoint in the Spec.
