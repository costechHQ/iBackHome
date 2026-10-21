---
id: WEB-OPS-011
title: "Audit log and agent runs"
stage: 11
surface: web
role: ops
priority: P0
fr: ["FR-23"]
route: "/ops/audit, /ops/agent-runs"
suggested_target: "web/src/features/ops-console/"
api: ["GET /ops/audit"]
links_to: []
states: ["default", "audit-log", "agent-runs-log", "loading", "error"]
inventory_refs: ["OP-12", "OP-16"]
missing_endpoints: ["MX-18", "MX-22"]
source_boards: ["Op-Audit.dc.html"]
---

# WEB-OPS-011 · Audit log and agent runs

## 1. Purpose

Search the read-only audit log; inspect agent runs with every tool call.

From the approved board (`Op-Audit.dc.html`): "Two records nobody can edit. The audit log is searchable, with before and after detail for every change. The agent runs log shows each AI run with its exact tool calls, so any report can be traced and re-run."

Stage 1 inventory: OP-12, OP-16. Priority P0 · FRs FR-23.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Audit log | desktop | 1440×900 | [desktop.png](desktop.png) |
| 2 | Agent runs log | desktop | 1440×900 | [desktop-02-agent-runs-log.png](desktop-02-agent-runs-log.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Text input and select, Search and filters, Status chip, Alert and banner, Ledger row and receipt, Evidence card, Quote check result, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Audit rows | GET /ops/audit -> actor, action, object_type, object_id, before, after, ip, device_id, at |
| Agent runs | agent_runs.agent, input, tool_calls, output, model, status, duration_ms: see MX-18 |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Export CSV".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /ops/audit`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-18: Agent runs log
- MX-22: Receipts and exports

## 5. States and error cases

Designed states: Audit log; Agent runs log.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Every money movement and sensitive action is audit-logged; the audit log is read-only.
- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).

## 7. Responsive and accessibility notes

- Designed variants: desktop (2).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[model version]`, `[2246, 2248]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-18: List agent_runs with tool calls for ops. No endpoint in the Spec.
- MX-22: Release receipt PDF, ledger CSV export and audit log export. No endpoints in the Spec.
