---
id: WEB-CLIENT-018
title: "Weekly reports"
stage: 7
surface: web
role: client
priority: P0
fr: ["FR-18"]
route: "/projects/:id/reports, /projects/:id/reports/:reportId"
suggested_target: "web/src/features/reports/"
api: ["GET /projects/{id}/reports"]
links_to: ["WEB-CLIENT-005", "WEB-CLIENT-009", "WEB-CLIENT-010", "WEB-CLIENT-011", "WEB-CLIENT-012", "WEB-CLIENT-013", "WEB-CLIENT-017", "WEB-CLIENT-019", "WEB-CLIENT-020"]
states: ["default", "list", "list", "report-viewer", "report-viewer", "loading", "error"]
inventory_refs: ["CM-08", "CM-09"]
missing_endpoints: ["MX-13"]
source_boards: ["Reports.dc.html"]
---

# WEB-CLIENT-018 · Weekly reports

## 1. Purpose

Report list and report viewer: AI-generated, reviewed by the supervisor, citing evidence IDs, money from the ledger.

From the approved board (`Reports.dc.html`): "One report a week, drafted every Friday by the AI report assistant from the project's own data and checked by the supervisor before it's sent. It always says it's AI-generated, every claim cites evidence by ID, and money figures come only from the ledger."

Stage 1 inventory: CM-08, CM-09. Priority P0 · FRs FR-18.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | List | desktop | 1280×900 | [desktop.png](desktop.png) |
| 2 | List | mobile | 390×844 | [mobile.png](mobile.png) |
| 3 | Report viewer | desktop | 1280×1840 | [desktop-02-report-viewer.png](desktop-02-report-viewer.png) |
| 4 | Report viewer | mobile | 390×1840 | [mobile-02-report-viewer.png](mobile-02-report-viewer.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Project tabs, Client bottom nav, Status chip, Money display, Escrow trust line, Ledger row and receipt, Milestone stepper, Evidence card, Checklist row, AI-generated label, Reviewed-by badge, Table, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Report list | GET /projects/{id}/reports -> week_start, status, sent_at |
| Report body | reports.body_md (AI-generated, see MX-13 for one report) |
| Cited evidence | reports.evidence_ids |
| Reviewed by | reviewer from audit log / review action: see MX-13 |
| Client-currency amount | ledger entry amount_minor + currency (client_funding, GBP/USD/EUR) |
| NGN equivalent | ledger entry on escrow:{project}:NGN |
| Rate | ledger_entries.fx_rate recorded at conversion (show with the funding date) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Download PDF".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/reports`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-13: Report detail, edit and PDF

Navigates to: WEB-CLIENT-005, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-013, WEB-CLIENT-017, WEB-CLIENT-019, WEB-CLIENT-020.

## 5. States and error cases

Designed states: List; List; Report viewer; Report viewer.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).

Designer note on the board (`Reports.dc.html`), **How the report stays honest**:

> The assistant only reads this project's evidence, verifications, ledger, BoQ and flags for the week. It writes facts, not advice, and every statement about the site cites the evidence it came from.
> Money lines are filled from the ledger by code, not written by the model, and show the ledger reference.
> Contractor uploads can be cited, but are always labelled as contractor uploads that don't count toward verification.
> The supervisor can correct the draft and add a note before marking it reviewed. His note is shown separately, under his name.
> The prompt and model version are stored with each report, so any report can be re-run and checked.

## 7. Responsive and accessibility notes

- Designed variants: desktop (2), mobile (2).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- The PDF layout itself was not designed (only the link).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-13: Read one report (body, evidence IDs, PDF link) and edit a draft before review. The Spec has list and review only.
