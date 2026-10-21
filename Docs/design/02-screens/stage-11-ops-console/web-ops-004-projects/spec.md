---
id: WEB-OPS-004
title: "Projects, BoQ approval and rotation"
stage: 11
surface: web
role: ops
priority: P0
fr: ["FR-03", "FR-04", "FR-05", "FR-11", "FR-19"]
route: "/ops/projects, /ops/projects/:id"
suggested_target: "web/src/features/ops-console/"
api: ["GET /projects", "GET /projects/{id}", "POST /projects/{id}/supervisor", "PUT /projects/{id}/site", "GET /projects/{id}/boq", "POST /projects/{id}/boq/approve"]
links_to: []
states: ["default", "projects-list", "project-detail-pause-site-supervisor-rotation", "boq-ops-approval-emekas-duplex-v2", "loading", "error"]
inventory_refs: ["OP-03", "OP-04", "OP-05", "OP-06"]
missing_endpoints: ["MX-08", "MX-09", "MX-15"]
source_boards: ["Op-Projects.dc.html"]
---

# WEB-OPS-004 · Projects, BoQ approval and rotation

## 1. Purpose

Projects list, project detail (pause, site boundary, supervisor rotation with relation blocks) and the ops BoQ approval.

From the approved board (`Op-Projects.dc.html`): "Ops can pause or resume a project, edit a locked site boundary (with a reason and a second approver), approve BoQs as the iBackHome party, and manage supervisor rotation. The system blocks any supervisor with a declared relationship to the contractor and says why."

Stage 1 inventory: OP-03, OP-04, OP-05, OP-06. Priority P0 · FRs FR-03, FR-04, FR-05, FR-11, FR-19.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Projects list | desktop | 1440×900 | [desktop.png](desktop.png) |
| 2 | Project detail · pause, site, supervisor rotation | desktop | 1440×900 | [desktop-02-project-detail-pause-site-supervisor.png](desktop-02-project-detail-pause-site-supervisor.png) |
| 3 | BoQ ops approval · Emeka's duplex v2 | desktop | 1440×900 | [desktop-03-boq-ops-approval-emekas-duplex-v2.png](desktop-03-boq-ops-approval-emekas-duplex-v2.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Text input and select, Segmented control and tabs, Search and filters, Status chip, Alert and banner, Escrow trust line, Milestone stepper, Geofence map, Quote check result, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Project title | projects.title (GET /projects/{id}) |
| Address | projects.address |
| Project status chip | projects.status |
| Budget | projects.budget_minor + projects.currency |
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |
| Milestone groups and lines | GET /projects/{id}/boq -> milestone_sequence, milestone_name, line_no, description, unit, quantity, unit_price_minor, total_minor |
| BoQ total vs budget | boq totals + projects.budget_minor |
| Who has approved | boq_approvals[]: role, user, approved_at |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Filters", "Pause project", "Edit boundary", "Assign", "Blocked", "Approve as ops", "Send back".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects`
- `GET /projects/{id}`
- `POST /projects/{id}/supervisor`
- `PUT /projects/{id}/site`
- `GET /projects/{id}/boq`
- `POST /projects/{id}/boq/approve`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-08: Send the BoQ back
- MX-09: Pause and resume a project
- MX-15: Supervisor directory and vetting detail

## 5. States and error cases

Designed states: Projects list; Project detail · pause, site, supervisor rotation; BoQ ops approval · Emeka's duplex v2.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `site_not_set`.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- The client can set or change the site only in draft or boq_review (409 site_locked after); the pin must be inside the polygon (422 pin_outside_geofence).
- BoQ line totals are computed by the server (422 boq_total_mismatch on mismatch); funding opens only after client, contractor and ops approve; the final approval needs a saved site (409 site_not_set).
- Every money movement and sensitive action is audit-logged; the audit log is read-only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."

## 7. Responsive and accessibility notes

- Designed variants: desktop (3).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- The design asks for a written reason and a second ops approval to edit a locked boundary; the Spec only says ops can change it at any time and it is audited.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-08: The boq_review -> draft transition (client, contractor or ops, with a reason) has no endpoint.
- MX-09: The ops-only active <-> paused transition has no endpoint.
- MX-15: List vetted supervisors with load and declared relations for assignment, and read one application for vetting. The Spec has assign, the vetting decision and the ops queue.
