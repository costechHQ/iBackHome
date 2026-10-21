---
id: AND-SUPERVISOR-011
title: "Weekly report review"
stage: 9
surface: android
role: supervisor
priority: P0
fr: ["FR-18"]
route: "ReportReviewScreen"
suggested_target: "mobile/lib/features/reports/ (new folder; not in the Spec)"
api: ["GET /projects/{id}/reports", "POST /reports/{id}/review"]
links_to: []
states: ["default", "read-the-ai-draft-fri-8-jan-16-10", "edit-the-draft", "mark-reviewed", "loading", "error"]
inventory_refs: ["SV-09"]
missing_endpoints: ["MX-13"]
source_boards: ["Sup-Report.dc.html"]
---

# AND-SUPERVISOR-011 · Weekly report review

## 1. Purpose

Read the AI draft, edit it, and mark it reviewed so it is sent.

From the approved board (`Sup-Report.dc.html`): "Every Friday the AI drafts each report, and only the assigned supervisor (or iBackHome) can mark it reviewed, which sends it. He reads it, can correct sentences and add a note under his own name, but can't touch the money lines. The client always sees both labels: AI-generated and reviewed."

Stage 1 inventory: SV-09. Priority P0 · FRs FR-18.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Read the AI draft · Fri 8 Jan, 16:10 | android | 360×800 | [android.png](android.png) |
| 2 | Edit the draft | android | 360×800 | [android-02-edit-the-draft.png](android-02-edit-the-draft.png) |
| 3 | Mark reviewed | android | 360×800 | [android-03-mark-reviewed.png](android-03-mark-reviewed.png) |

Components (see [components.md](../../../01-design-system/components.md)): Android app bar and bottom nav, Buttons, Text input and select, Status chip, Dialog and alert dialog, Bottom sheet and side panel, Escrow trust line, Evidence card, AI-generated label, Reviewed-by badge, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Report list | GET /projects/{id}/reports -> week_start, status, sent_at |
| Report body | reports.body_md (AI-generated, see MX-13 for one report) |
| Cited evidence | reports.evidence_ids |
| Reviewed by | reviewer from audit log / review action: see MX-13 |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Edit", "Mark reviewed", "Save", "Keep editing".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /projects/{id}/reports`
- `POST /reports/{id}/review`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-13: Report detail, edit and PDF

## 5. States and error cases

Designed states: Read the AI draft · Fri 8 Jan, 16:10; Edit the draft; Mark reviewed.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.

## 7. Responsive and accessibility notes

- Designed variants: android (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- CONFLICT TO DECIDE: this board designs an "Edit the draft" step, but Stage 1 assumption G-17 said reviewers cannot free-text edit AI output. The Spec has no edit endpoint (MX-13).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-13: Read one report (body, evidence IDs, PDF link) and edit a draft before review. The Spec has list and review only.
