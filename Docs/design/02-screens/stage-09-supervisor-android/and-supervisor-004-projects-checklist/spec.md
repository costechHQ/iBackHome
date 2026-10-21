---
id: AND-SUPERVISOR-004
title: "Assigned projects and checklist"
stage: 9
surface: android
role: supervisor
priority: P0
fr: ["FR-03", "FR-12"]
route: "ProjectsScreen, ProjectDetailScreen, ChecklistScreen"
suggested_target: "mobile/lib/features/projects/"
api: ["GET /projects", "GET /projects/{id}", "GET /projects/{id}/milestones"]
links_to: []
states: ["default", "assigned-projects-wed-6-jan-08-40", "project-detail", "milestone-checklist", "loading", "error"]
inventory_refs: ["SV-01", "SV-02"]
missing_endpoints: []
source_boards: ["Sup-Projects.dc.html"]
---

# AND-SUPERVISOR-004 · Assigned projects and checklist

## 1. Purpose

Assigned sites with sync status, project detail, and the milestone checklist (from ops templates).

From the approved board (`Sup-Projects.dc.html`): "Chidi Nnaji's home in the supervisor app: what to visit today, every project he's assigned, and the exact checklist he must capture. Plain lists, 48dp rows, one primary action per screen. Times are in Enugu (WAT)."

Stage 1 inventory: SV-01, SV-02. Priority P0 · FRs FR-03, FR-12.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Assigned projects · Wed 6 Jan, 08:40 | android | 360×800 | [android.png](android.png) |
| 2 | Project detail | android | 360×800 | [android-02-project-detail.png](android-02-project-detail.png) |
| 3 | Milestone checklist | android | 360×800 | [android-03-milestone-checklist.png](android-03-milestone-checklist.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Android app bar and bottom nav, Buttons, Status chip, Milestone stepper, Checklist row, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Project cards | GET /projects -> items[]: id, title, address, status, budget_minor, currency |
| Milestone name and order | GET /projects/{id}/milestones -> name, sequence |
| Amount | amount_minor + currency (NGN) |
| Status chip and stepper node | milestones.status |
| Dates | funded_at, claimed_at, verified_at, approved_at, released_at (UTC, shown in viewer time zone) |
| Supervisor checklist and notes | newest verification: checklist (JSONB), notes, decision |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Call Engr. Obi", "Start Plastering visit", "Start visit".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects`
- `GET /projects/{id}`
- `GET /projects/{id}/milestones`

## 5. States and error cases

Designed states: Assigned projects · Wed 6 Jan, 08:40; Project detail; Milestone checklist.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- Role and project membership are checked on every request; each role sees only its own screens.

Designer note on the board (`Sup-Projects.dc.html`), **Built for low-end phones**:

> Flat colours, no blur and no shadows. Lists don't load images; thumbnails appear only when a photo is opened.
> The project list works offline from the last sync. The sync strip always says when that was.
> Released milestones are read-only. A supervisor can only act on the milestones he's assigned.

## 7. Responsive and accessibility notes

- Designed variants: android (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- Checklists come from ops templates (Stage 1 assumption); the Spec has no template endpoint, so they arrive inside the milestone/verification data.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
