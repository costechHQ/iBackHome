---
id: WEB-OPS-007
title: "Spot-check scheduler"
stage: 11
surface: web
role: ops
priority: P1
fr: ["FR-11", "FR-19"]
route: "/ops/spot-checks"
suggested_target: "web/src/features/ops-console/"
api: ["POST /projects/{id}/spot-checks"]
links_to: []
states: ["default", "spot-check-scheduler-and-results", "loading", "error"]
inventory_refs: ["OP-14"]
missing_endpoints: ["MX-14", "MX-15"]
source_boards: ["Op-SpotChecks.dc.html"]
---

# WEB-OPS-007 · Spot-check scheduler

## 1. Purpose

Schedule an unannounced visit by an eligible supervisor and review results before sharing with the client.

From the approved board (`Op-SpotChecks.dc.html`): "Ops schedules unannounced visits by a supervisor from another project, with no link to the contractor. Nothing appears for the contractor, and the client sees a spot check only once ops closes it. Results that don't match a claim can be linked straight to a dispute."

Stage 1 inventory: OP-14. Priority P1 · FRs FR-11, FR-19.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Spot-check scheduler and results | desktop | 1440×900 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Text input and select, Search and filters, Status chip, Alert and banner, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Spot checks | spot_checks.project, scheduled_for, completed_at, findings |
| Supervisor | spot_checks.supervisor -> users.full_name |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Schedule spot check", "Review", "Close and share with client", "Link to D-0066".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /projects/{id}/spot-checks`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-14: Spot-check history and sharing
- MX-15: Supervisor directory and vetting detail

## 5. States and error cases

Designed states: Spot-check scheduler and results.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Spot checks are unannounced: the contractor is never notified; the client sees results only after ops closes them.
- A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-14: Client and ops lists of completed spot checks, and ops "share with client" after closing. The Spec has the supervisor's list, schedule and complete only.
- MX-15: List vetted supervisors with load and declared relations for assignment, and read one application for vetting. The Spec has assign, the vetting decision and the ops queue.
