---
id: AND-SUPERVISOR-010
title: "Spot checks"
stage: 9
surface: android
role: supervisor
priority: P1
fr: ["FR-11"]
route: "SpotChecksScreen"
suggested_target: "mobile/lib/features/spot_checks/"
api: ["GET /supervisors/me/spot-checks", "POST /spot-checks/{id}/complete", "POST /evidence/upload-url", "POST /evidence"]
links_to: []
states: ["default", "spot-checks-thu-7-jan-09-00", "complete-with-findings", "findings-submitted", "loading", "error"]
inventory_refs: ["SV-11", "SV-12"]
missing_endpoints: []
source_boards: ["Sup-SpotChecks.dc.html"]
---

# AND-SUPERVISOR-010 · Spot checks

## 1. Purpose

Unannounced visits to make, complete with captures and findings, submitted.

From the approved board (`Sup-SpotChecks.dc.html`): "Unannounced visits that iBackHome assigns to a supervisor from another project. The form is short and factual, with the same capture rules as a normal visit. The contractor is never told in advance, and the client only sees a spot check once it's closed."

Stage 1 inventory: SV-11, SV-12. Priority P1 · FRs FR-11.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Spot checks · Thu 7 Jan, 09:00 | android | 360×800 | [android.png](android.png) |
| 2 | Complete with findings | android | 360×800 | [android-02-complete-with-findings.png](android-02-complete-with-findings.png) |
| 3 | Findings submitted | android | 360×800 | [android-03-findings-submitted.png](android-03-findings-submitted.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Android app bar and bottom nav, Buttons, Text input and select, Status chip, Alert and banner, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Spot checks | spot_checks.project, scheduled_for, completed_at, findings |
| Supervisor | spot_checks.supervisor -> users.full_name |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Submit findings", "Back to spot checks".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /supervisors/me/spot-checks`
- `POST /spot-checks/{id}/complete`
- `POST /evidence/upload-url`
- `POST /evidence`

## 5. States and error cases

Designed states: Spot checks · Thu 7 Jan, 09:00; Complete with findings; Findings submitted.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Spot checks are unannounced: the contractor is never notified; the client sees results only after ops closes them.
- Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.

## 7. Responsive and accessibility notes

- Designed variants: android (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
