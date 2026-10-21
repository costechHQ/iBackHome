---
id: WEB-OPS-012
title: "Users and status"
stage: 11
surface: web
role: ops
priority: P1
fr: ["FR-01", "FR-23"]
route: "/ops/users"
suggested_target: "web/src/features/ops-console/"
api: []
links_to: []
states: ["default", "user-management-role-and-status", "loading", "error"]
inventory_refs: []
missing_endpoints: ["MX-17", "MX-02"]
source_boards: ["Op-Users.dc.html"]
---

# WEB-OPS-012 · Users and status

## 1. Purpose

Users by role with status changes (suspend) that need a reason.

From the approved board (`Op-Users.dc.html`): "Everyone on the platform, filtered by role. Changing a status needs a reason and shows the knock-on effects first, such as projects that will need cover. Every change goes in the audit log."

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | User management · role and status | desktop | 1440×900 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Text input and select, Segmented control and tabs, Search and filters, Status chip, Alert and banner, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| User rows | users.full_name, role, status, country (see MX-17) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Invite ops user", "Suspend user", "Cancel".

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-17: User administration
- MX-02: Project invitations

## 5. States and error cases

Designed states: User management · role and status.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Every money movement and sensitive action is audit-logged; the audit log is read-only.
- Role and project membership are checked on every request; each role sees only its own screens.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Not in the Stage 1 inventory; added in Stage 11. INCONSISTENT: "Deactivated" status is not in users.status (active, suspended).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-17: List users and change a user's status (suspend). The Spec has no user admin endpoints.
- MX-02: View, accept, decline, resend and cancel an invitation (contractor by client; supplier and ops user by ops). The Spec only says POST /projects "invites contractor".
