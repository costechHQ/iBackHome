---
id: WEB-OPS-002
title: "Overview, live map and money alerts"
stage: 11
surface: web
role: ops
priority: P0
fr: ["FR-19", "FR-14", "FR-23"]
route: "/ops"
suggested_target: "web/src/features/ops-console/"
api: ["GET /ops/queue", "GET /projects"]
links_to: []
states: ["default", "overview-mon-11-jan-2027-09-30-wat", "loading", "error"]
inventory_refs: ["OP-01", "OP-09", "OP-11"]
missing_endpoints: ["MX-21"]
source_boards: ["Op-Overview.dc.html"]
---

# WEB-OPS-002 · Overview, live map and money alerts

## 1. Purpose

Queue counts, failed releases and reconciliation mismatches, live map of all sites and today on site.

From the approved board (`Op-Overview.dc.html`): "The ops console uses the client theme in a denser layout: 13px body text, compact tables and a dark navy sidebar so staff always know they're in the admin tool. The overview answers three questions: what's waiting in the queues, what's broken with money, and where every site is."

Stage 1 inventory: OP-01, OP-09, OP-11. Priority P0 · FRs FR-19, FR-14, FR-23.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Overview · Mon 11 Jan 2027, 09:30 WAT | desktop | 1440×900 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Segmented control and tabs, Search and filters, Status chip, Alert and banner, Ledger row and receipt, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Queue counts and items | GET /ops/queue -> vetting, flagged evidence, disputes |
| Project cards | GET /projects -> items[]: id, title, address, status, budget_minor, currency |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Retry release", "Open", "Compare records".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /ops/queue`
- `GET /projects`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-21: Ops money alerts and release retry

## 5. States and error cases

Designed states: Overview · Mon 11 Jan 2027, 09:30 WAT.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Every money movement and sensitive action is audit-logged; the audit log is read-only.
- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-21: List failed releases and reconciliation mismatches, and retry a failed release. The Spec sends alerts by console and email but lists no endpoint.
