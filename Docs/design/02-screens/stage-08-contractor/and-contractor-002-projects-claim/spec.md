---
id: AND-CONTRACTOR-002
title: "Projects and claim (Android)"
stage: 8
surface: android
role: contractor
priority: P0
fr: ["FR-12", "FR-03"]
route: "ProjectsScreen, MilestoneScreen"
suggested_target: "mobile/lib/features/projects/ + mobile/lib/features/milestones/"
api: ["GET /projects", "GET /projects/{id}/milestones", "POST /milestones/{id}/claim"]
links_to: []
states: ["default", "projects-mon-4-jan", "milestone-ready-to-claim", "claim-confirmation", "loading", "error"]
inventory_refs: ["CO-01", "CO-02", "CO-05"]
missing_endpoints: []
source_boards: ["Con-Android.dc.html"]
---

# AND-CONTRACTOR-002 · Projects and claim (Android)

## 1. Purpose

Contractor app: projects, a milestone ready to claim, and the claim confirmation.

From the approved board (`Con-Android.dc.html`): "The same app as the supervisor's, with the contractor's role: see projects, claim a milestone on site, take contractor photos, follow orders and alerts. Uses the Stage 2 Android kit: 48dp targets, flat surfaces, in-app camera only. Every contractor photo is labelled as contractor evidence from shutter to gallery."

Stage 1 inventory: CO-01, CO-02, CO-05. Priority P0 · FRs FR-12, FR-03.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Projects · Mon 4 Jan | android | 360×800 | [android.png](android.png) |
| 2 | Milestone · ready to claim | android | 360×800 | [android-02-milestone-ready-to-claim.png](android-02-milestone-ready-to-claim.png) |
| 3 | Claim confirmation | android | 360×800 | [android-03-claim-confirmation.png](android-03-claim-confirmation.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Contractor app bottom nav, Buttons, Status chip, Dialog and alert dialog, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |
| Dates | funded_at, claimed_at, verified_at, approved_at, released_at (UTC, shown in viewer time zone) |
| Supervisor checklist and notes | newest verification: checklist (JSONB), notes, decision |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Add contractor photo", "Claim milestone", "Cancel".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects`
- `GET /projects/{id}/milestones`
- `POST /milestones/{id}/claim`

## 5. States and error cases

Designed states: Projects · Mon 4 Jan; Milestone · ready to claim; Claim confirmation.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.

## 7. Responsive and accessibility notes

- Designed variants: android (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[3 working days]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
