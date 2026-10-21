---
id: AND-SUPERVISOR-001
title: "Supervisor application and vetting status"
stage: 4
surface: android
role: supervisor
priority: P0
fr: ["FR-02"]
route: "SupervisorApplicationScreen"
suggested_target: "mobile/lib/features/auth/ (vetting; Spec puts vetting under backend supervision/)"
api: ["PUT /supervisors/me/profile", "GET /supervisors/me/profile"]
links_to: []
states: ["default", "1-start-application", "2-registration", "3-nin", "4-guarantors", "5-relatives-who-are-contractors", "6-review-and-submit", "7-pending", "8-rejected-with-reason", "9-approved", "loading", "error"]
inventory_refs: ["AU-07", "AU-08"]
missing_endpoints: []
source_boards: ["Onboard-Supervisor.dc.html"]
---

# AND-SUPERVISOR-001 · Supervisor application and vetting status

## 1. Purpose

Apply for vetting in the app: registration (COREN or NIOB), NIN, two guarantors, declared relatives; then pending, rejected with reason, or approved.

From the approved board (`Onboard-Supervisor.dc.html`): "From "Apply" on the public site, the supervisor signs in with a code in the app, completes five steps, and waits for ops. After approval: permissions, then the secure capture key that signs every photo. No site can be assigned until vetting is approved."

Stage 1 inventory: AU-07, AU-08. Priority P0 · FRs FR-02.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | 1 · Start application | android | 360×800 | [android.png](android.png) |
| 2 | 2 · Registration | android | 360×800 | [android-02-2-registration.png](android-02-2-registration.png) |
| 3 | 3 · NIN | android | 360×800 | [android-03-3-nin.png](android-03-3-nin.png) |
| 4 | 4 · Guarantors | android | 360×800 | [android-04-4-guarantors.png](android-04-4-guarantors.png) |
| 5 | 5 · Relatives who are contractors | android | 360×800 | [android-05-5-relatives-who-are-contractors.png](android-05-5-relatives-who-are-contractors.png) |
| 6 | 6 · Review and submit | android | 360×800 | [android-06-6-review-and-submit.png](android-06-6-review-and-submit.png) |
| 7 | 7 · Pending | android | 360×800 | [android-07-7-pending.png](android-07-7-pending.png) |
| 8 | 8 · Rejected, with reason | android | 360×800 | [android-08-8-rejected-with-reason.png](android-08-8-rejected-with-reason.png) |
| 9 | 9 · Approved | android | 360×800 | [android-09-9-approved.png](android-09-9-approved.png) |

Components (see [components.md](../../../01-design-system/components.md)): Buttons, Status chip, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Registration body and number | supervisor_profiles.registration_body, registration_no |
| NIN | nin_verified (only the last 4 digits are shown) |
| Guarantors | guarantor_1, guarantor_2, *_verified |
| Declared relatives | supervisor_relations[]: contractor_phone, relationship |
| Vetting status | vetting_status: pending \| approved \| rejected, rejection_reason |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Start", "Continue", "+ Add another relative", "Submit application", "Refresh status", "Fix and re-apply", "Contact our team", "Set up this phone".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `PUT /supervisors/me/profile`
- `GET /supervisors/me/profile`

## 5. States and error cases

Designed states: 1 · Start application; 2 · Registration; 3 · NIN; 4 · Guarantors; 5 · Relatives who are contractors; 6 · Review and submit; 7 · Pending; 8 · Rejected, with reason; 9 · Approved.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.

## 7. Responsive and accessibility notes

- Designed variants: android (9).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- Both COREN and NIOB are accepted (user decision, Stage 4).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
