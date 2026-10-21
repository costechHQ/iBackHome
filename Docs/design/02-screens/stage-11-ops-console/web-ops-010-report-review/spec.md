---
id: WEB-OPS-010
title: "Weekly report review (ops)"
stage: 11
surface: web
role: ops
priority: P0
fr: ["FR-18"]
route: "/ops/reports"
suggested_target: "web/src/features/ops-console/"
api: ["GET /projects/{id}/reports", "POST /reports/{id}/review"]
links_to: []
states: ["default", "weekly-report-review", "loading", "error"]
inventory_refs: ["OP-10"]
missing_endpoints: ["MX-13"]
source_boards: ["Op-Reports.dc.html"]
---

# WEB-OPS-010 · Weekly report review (ops)

## 1. Purpose

Review AI drafts that are late or where the supervisor is involved, and mark them reviewed.

From the approved board (`Op-Reports.dc.html`): "Every Friday's drafts in one queue, showing who should review each and whether it went out. Ops steps in when a review is late or the supervisor is involved in a dispute, and the report then says "Reviewed by iBackHome"."

Stage 1 inventory: OP-10. Priority P0 · FRs FR-18.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Weekly report review | desktop | 1440×900 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Text input and select, Search and filters, Status chip, Alert and banner, Escrow trust line, Evidence card, AI-generated label, Reviewed-by badge, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Report list | GET /projects/{id}/reports -> week_start, status, sent_at |
| Report body | reports.body_md (AI-generated, see MX-13 for one report) |
| Cited evidence | reports.evidence_ids |
| Reviewed by | reviewer from audit log / review action: see MX-13 |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Mark reviewed and send", "Regenerate draft".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/reports`
- `POST /reports/{id}/review`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-13: Report detail, edit and PDF

## 5. States and error cases

Designed states: Weekly report review.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- "More than [48 hours] late" threshold is PLACEHOLDER.
- PLACEHOLDER values on this screen (in square brackets on the design): `[48 hours]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-13: Read one report (body, evidence IDs, PDF link) and edit a draft before review. The Spec has list and review only.
