---
id: WEB-SUPPLIER-006
title: "Business profile and bank"
stage: 10
surface: web
role: supplier
priority: P1
fr: ["FR-16"]
route: "/s/profile"
suggested_target: "web/src/features/suppliers/"
api: ["GET /me"]
links_to: ["WEB-SUPPLIER-002", "WEB-SUPPLIER-003", "WEB-SUPPLIER-005", "WEB-SUPPLIER-007"]
states: ["default", "desktop", "mobile-web", "loading", "error"]
inventory_refs: ["SU-04"]
missing_endpoints: ["MX-01", "MX-03", "MX-04"]
source_boards: ["Sp-Profile.dc.html"]
---

# WEB-SUPPLIER-006 · Business profile and bank

## 1. Purpose

Business profile, yard location and payout account (name-matched, masked).

From the approved board (`Sp-Profile.dc.html`): "What iBackHome knows about the supplier, and what others see. The bank account is always masked to the last 4 digits. Changing it is protected because it decides where escrow money goes."

Stage 1 inventory: SU-04. Priority P1 · FRs FR-16.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×900 | [desktop.png](desktop.png) |
| 2 | Mobile web | mobile | 390×844 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Supplier top bar and mobile nav, Buttons, Status chip, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Supplier rows | suppliers.name, address, location, verified, paystack_recipient_code (see MX-04) |
| Account | payout_recipients.bank_name, account_name, account_number_masked |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Edit", "Change payout account", "Edit business details", "Sign out".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /me`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-01: Update own profile and preferences
- MX-03: Payout recipient
- MX-04: Supplier business profile and verification

Navigates to: WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-005, WEB-SUPPLIER-007.

## 5. States and error cases

Designed states: Desktop; Mobile web.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[24 hours]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-01: Name, country, time zone, consent, notification channel order, quiet hours. The Spec has only GET /me.
- MX-03: Look up the account name, save, view and change the payout account for a contractor or supplier (payout_recipients table exists, no endpoint).
- MX-04: Create/update a supplier (name, address, location), ops verification steps and approve/suspend (suppliers table exists, no endpoint).
