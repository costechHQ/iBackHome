---
id: WEB-CONTRACTOR-002
title: "Contractor onboarding"
stage: 4
surface: web
role: contractor
priority: P0
fr: ["FR-01", "FR-03"]
route: "/welcome"
suggested_target: "web/src/features/auth/"
api: ["GET /me"]
links_to: []
states: ["default", "step-1-your-details", "step-2-payout-account-name-checked", "step-2-saved-number-masked", "home-waiting-for-your-boq", "loading", "error"]
inventory_refs: ["AU-04"]
missing_endpoints: ["MX-01", "MX-03"]
source_boards: ["Onboard-Contractor.dc.html"]
---

# WEB-CONTRACTOR-002 · Contractor onboarding

## 1. Purpose

Contractor details and payout account (name check, number masked after saving), then home waiting for the BoQ.

From the approved board (`Onboard-Contractor.dc.html`): "After accepting the invitation: profile, then payout bank details (the account name is checked with the bank and only the last four digits are kept), then home — where the next job is the bill of quantities. Web shown; Android uses the same steps."

Stage 1 inventory: AU-04. Priority P0 · FRs FR-01, FR-03.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Step 1 — your details | desktop | 1280×800 | [desktop.png](desktop.png) |
| 2 | Step 2 — payout account, name checked | desktop | 1280×800 | [desktop-02-step-2-payout-account-name-checked.png](desktop-02-step-2-payout-account-name-checked.png) |
| 3 | Step 2 — saved, number masked | desktop | 1280×800 | [desktop-03-step-2-saved-number-masked.png](desktop-03-step-2-saved-number-masked.png) |
| 4 | Home — waiting for your BoQ | desktop | 1280×800 | [desktop-04-home-waiting-for-your-boq.png](desktop-04-home-waiting-for-your-boq.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Buttons, Text input and select, Status chip, Milestone stepper, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Signed-in user | GET /me -> full_name, role, timezone, country, phone, email |
| Account | payout_recipients.bank_name, account_name, account_number_masked |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Back", "Continue", "Save payout account", "Go to my projects", "Start the BoQ".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /me`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-01: Update own profile and preferences
- MX-03: Payout recipient

## 5. States and error cases

Designed states: Step 1 — your details; Step 2 — payout account, name checked; Step 2 — saved, number masked; Home — waiting for your BoQ.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.

## 7. Responsive and accessibility notes

- Designed variants: desktop (4).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- CAC number is optional (Stage 1 assumption, confirmed).
- Account-name lookup provider (Paystack resolve) is not in the Spec API list.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-01: Name, country, time zone, consent, notification channel order, quiet hours. The Spec has only GET /me.
- MX-03: Look up the account name, save, view and change the payout account for a contractor or supplier (payout_recipients table exists, no endpoint).
