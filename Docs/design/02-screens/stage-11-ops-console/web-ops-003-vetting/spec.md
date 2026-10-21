---
id: WEB-OPS-003
title: "Supervisor vetting"
stage: 11
surface: web
role: ops
priority: P0
fr: ["FR-02", "FR-19"]
route: "/ops/vetting, /ops/vetting/:id"
suggested_target: "web/src/features/ops-console/"
api: ["GET /ops/queue", "POST /supervisors/{id}/vetting"]
links_to: []
states: ["default", "vetting-queue", "vetting-detail-decide", "loading", "error"]
inventory_refs: ["OP-02"]
missing_endpoints: ["MX-15"]
source_boards: ["Op-Vetting.dc.html"]
---

# WEB-OPS-003 · Supervisor vetting

## 1. Purpose

Vetting queue and detail: registration, NIN, guarantors, declared relatives; approve stays locked until all checks pass.

From the approved board (`Op-Vetting.dc.html`): "Every check the vetting rules require sits on one page: registration with COREN or NIOB, NIN, two guarantors confirmed by phone, and declared relationships. A declared relationship to a contractor doesn't block approval, but it permanently blocks assignment to that contractor's projects."

Stage 1 inventory: OP-02. Priority P0 · FRs FR-02, FR-19.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Vetting queue | desktop | 1440×900 | [desktop.png](desktop.png) |
| 2 | Vetting detail · decide | desktop | 1440×900 | [desktop-02-vetting-detail-decide.png](desktop-02-vetting-detail-decide.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Text input and select, Segmented control and tabs, Search and filters, Status chip, Alert and banner, Table, Card, Avatar (initials).

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

Actions on the design: "Approve applicant", "Ask for more information", "Reject".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /ops/queue`
- `POST /supervisors/{id}/vetting`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-15: Supervisor directory and vetting detail

## 5. States and error cases

Designed states: Vetting queue; Vetting detail · decide.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- Every money movement and sensitive action is audit-logged; the audit log is read-only.

## 7. Responsive and accessibility notes

- Designed variants: desktop (2).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-15: List vetted supervisors with load and declared relations for assignment, and read one application for vetting. The Spec has assign, the vetting decision and the ops queue.
