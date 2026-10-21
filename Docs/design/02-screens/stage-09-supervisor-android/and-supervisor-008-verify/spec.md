---
id: AND-SUPERVISOR-008
title: "Verify or send back"
stage: 9
surface: android
role: supervisor
priority: P0
fr: ["FR-12", "FR-14"]
route: "VerifyScreen"
suggested_target: "mobile/lib/features/milestones/"
api: ["POST /milestones/{id}/verify", "GET /projects/{id}/milestones"]
links_to: []
states: ["default", "verify-re-check-tue-12-jan", "send-back-with-reasons-wed-6-jan", "confirm-verification", "conflict-changed-while-offline", "loading", "error"]
inventory_refs: ["SV-07", "SV-08"]
missing_endpoints: []
source_boards: ["Sup-Verify.dc.html"]
---

# AND-SUPERVISOR-008 · Verify or send back

## 1. Purpose

Checklist with required evidence, verify or send back with reasons, confirm, and the 409 conflict when the milestone changed offline.

From the approved board (`Sup-Verify.dc.html`): "The supervisor can verify only when every checklist item has an accepted capture from this visit. Sending back needs a reason for each failed item, and those reasons are what the contractor and client see in Stage 8 and Stage 7. If the milestone changed on the server while he was offline, his queued decision is refused, the app says why, and his evidence still uploads."

Stage 1 inventory: SV-07, SV-08. Priority P0 · FRs FR-12, FR-14.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Verify · re-check Tue 12 Jan | android | 360×800 | [android.png](android.png) |
| 2 | Send back with reasons · Wed 6 Jan | android | 360×800 | [android-02-send-back-with-reasons-wed-6-jan.png](android-02-send-back-with-reasons-wed-6-jan.png) |
| 3 | Confirm verification | android | 360×800 | [android-03-confirm-verification.png](android-03-confirm-verification.png) |
| 4 | Conflict · changed while offline | android | 360×800 | [android-04-conflict-changed-while-offline.png](android-04-conflict-changed-while-offline.png) |

Components (see [components.md](../../../01-design-system/components.md)): Android app bar and bottom nav, Buttons, Text input and select, Status chip, Alert and banner, Dialog and alert dialog, Bottom sheet and side panel, Evidence card, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Supervisor checklist and notes | newest verification: checklist (JSONB), notes, decision |
| Status chip | evidence.status: pending_checks \| accepted \| flagged \| rejected |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Verify Plastering", "Send back to contractor", "Send back to Engr. Obi", "Verify", "Cancel", "Call iBackHome".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /milestones/{id}/verify`
- `GET /projects/{id}/milestones`

## 5. States and error cases

Designed states: Verify · re-check Tue 12 Jan; Send back with reasons · Wed 6 Jan; Confirm verification; Conflict · changed while offline.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `conflict_409`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.
- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- Every write sends an Idempotency-Key; disable the submit button while a write is in flight.

## 7. Responsive and accessibility notes

- Designed variants: android (4).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
