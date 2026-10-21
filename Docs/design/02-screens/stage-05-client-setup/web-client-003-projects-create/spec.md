---
id: WEB-CLIENT-003
title: "Projects and create project"
stage: 5
surface: web
role: client
priority: P0
fr: ["FR-03", "FR-05"]
route: "/projects, /projects/new, /projects/:id/setup"
suggested_target: "web/src/features/projects/"
api: ["GET /projects", "POST /projects", "GET /projects/{id}", "GET /projects/{id}/boq"]
links_to: ["WEB-CLIENT-020"]
states: ["default", "cs-01-projects-empty", "cs-01-projects-populated", "cs-02-cs-03-create-project-with-one-inline-error", "cs-05-set-up-tracker-with-supervisor-assigned", "projects", "create-project", "what-chioma-sees-meanwhile-set-up-tracker-row", "loading", "error"]
inventory_refs: ["CS-01", "CS-02", "CS-03", "CS-05"]
missing_endpoints: ["MX-02"]
source_boards: ["Auth-Invite.dc.html", "Setup-Projects.dc.html"]
---

# WEB-CLIENT-003 · Projects and create project

## 1. Purpose

List projects (empty and populated), create a project and invite the contractor, then follow the set-up tracker (contractor, site, supervisor, BoQ, funding).

From the approved board (`Setup-Projects.dc.html`): "A client can have more than one project. Creating one takes four fields plus the contractor's number; everything else happens on the set-up tracker, which always shows the single next action."

From the approved board (`Auth-Invite.dc.html`): "Chioma invites Engr. Obi by phone. He gets a WhatsApp link, sees what he's joining, confirms with a code sent to the invited number, and lands in contractor onboarding. Mostly on a phone, so mobile first."

Stage 1 inventory: CS-01, CS-02, CS-03, CS-05. Priority P0 · FRs FR-03, FR-05.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | CS-01 · Projects — empty | desktop | 1280×800 | [desktop.png](desktop.png) |
| 2 | CS-01 · Projects — populated | desktop | 1280×800 | [desktop-02-cs-01-projects-populated.png](desktop-02-cs-01-projects-populated.png) |
| 3 | CS-02, CS-03 · Create project — with one inline error | desktop | 1280×800 | [desktop-03-cs-02-cs-03-create-project-with-one.png](desktop-03-cs-02-cs-03-create-project-with-one.png) |
| 4 | CS-05 · Set-up tracker, with supervisor assigned | desktop | 1280×800 | [desktop-04-cs-05-set-up-tracker-with-supervisor.png](desktop-04-cs-05-set-up-tracker-with-supervisor.png) |
| 5 | Projects | mobile | 390×844 | [mobile.png](mobile.png) |
| 6 | Create project | mobile | 390×844 | [mobile-02-create-project.png](mobile-02-create-project.png) |
| 7 | What Chioma sees meanwhile (set-up tracker row) | panel | 602×327 | [panel.png](panel.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Buttons, Text input and select, Status chip, Empty state, Escrow trust line, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Project cards | GET /projects -> items[]: id, title, address, status, budget_minor, currency |
| Next action per project | derived from milestones[].status (verified -> approve) |
| Project title | projects.title (GET /projects/{id}) |
| Address | projects.address |
| Project status chip | projects.status |
| Budget | projects.budget_minor + projects.currency |
| Client / contractor / supervisor names | projects.client, projects.contractor, projects.supervisor -> users.full_name |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Create your first project", "New project", "Cancel", "Create and invite", "View map", "Review BoQ", "Resend invitation", "Invite someone else".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects`
- `POST /projects`
- `GET /projects/{id}`
- `GET /projects/{id}/boq`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-02: Project invitations

Navigates to: WEB-CLIENT-020.

## 5. States and error cases

Designed states: CS-01 · Projects — empty; CS-01 · Projects — populated; CS-02, CS-03 · Create project — with one inline error; CS-05 · Set-up tracker, with supervisor assigned; Projects; Create project; What Chioma sees meanwhile (set-up tracker row).

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Role and project membership are checked on every request; each role sees only its own screens.
- Every write sends an Idempotency-Key; disable the submit button while a write is in flight.

## 7. Responsive and accessibility notes

- Designed variants: desktop (4), mobile (2), panel (1).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Project create validation messages are design copy; the Spec defines no field-level error codes.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-02: View, accept, decline, resend and cancel an invitation (contractor by client; supplier and ops user by ops). The Spec only says POST /projects "invites contractor".
