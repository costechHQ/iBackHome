---
id: AND-CONTRACTOR-001
title: "Contractor onboarding (Android)"
stage: 4
surface: android
role: contractor
priority: P0
fr: ["FR-01", "FR-03"]
route: "ContractorOnboardingScreen"
suggested_target: "mobile/lib/features/auth/"
api: ["GET /me"]
links_to: []
states: ["default", "payout-name-found", "payout-not-found", "home-waiting-for-boq", "loading", "error"]
inventory_refs: ["AU-04"]
missing_endpoints: ["MX-01", "MX-03"]
source_boards: ["Onboard-Contractor.dc.html"]
---

# AND-CONTRACTOR-001 · Contractor onboarding (Android)

## 1. Purpose

Contractor payout account on Android (name found / not found) and home waiting for the BoQ.

From the approved board (`Onboard-Contractor.dc.html`): "After accepting the invitation: profile, then payout bank details (the account name is checked with the bank and only the last four digits are kept), then home — where the next job is the bill of quantities. Web shown; Android uses the same steps."

Stage 1 inventory: AU-04. Priority P0 · FRs FR-01, FR-03.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Payout — name found | android | 360×800 | [android.png](android.png) |
| 2 | Payout — not found | android | 360×800 | [android-02-payout-not-found.png](android-02-payout-not-found.png) |
| 3 | Home — waiting for BoQ | android | 360×800 | [android-03-home-waiting-for-boq.png](android-03-home-waiting-for-boq.png) |

Components (see [components.md](../../../01-design-system/components.md)): Buttons, Status chip, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Account | payout_recipients.bank_name, account_name, account_number_masked |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Save payout account", "Email me the link".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /me`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-01: Update own profile and preferences
- MX-03: Payout recipient

## 5. States and error cases

Designed states: Payout — name found; Payout — not found; Home — waiting for BoQ.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.

## 7. Responsive and accessibility notes

- Designed variants: android (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-01: Name, country, time zone, consent, notification channel order, quiet hours. The Spec has only GET /me.
- MX-03: Look up the account name, save, view and change the payout account for a contractor or supplier (payout_recipients table exists, no endpoint).
