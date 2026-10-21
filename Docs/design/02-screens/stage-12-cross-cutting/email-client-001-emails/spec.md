---
id: EMAIL-CLIENT-001
title: "Client emails"
stage: 12
surface: email
role: client
priority: P1
fr: ["FR-20", "FR-18"]
route: "templates: milestone_verified, weekly_report"
suggested_target: "backend/app/base/notifications/ (email templates)"
api: []
links_to: []
states: ["default", "milestone-verified", "weekly-report", "loading", "error"]
inventory_refs: ["NS-03"]
missing_endpoints: []
source_boards: ["X-Email.dc.html"]
---

# EMAIL-CLIENT-001 · Client emails

## 1. Purpose

Milestone verified and weekly report emails with both currencies, the escrow line and a preferences link.

From the approved board (`X-Email.dc.html`): "The two emails clients get alongside WhatsApp. They use the web brand, a plain layout that renders in any mail app, one primary button, both currencies, the escrow line, and an unsubscribe-style preferences link."

Stage 1 inventory: NS-03. Priority P1 · FRs FR-20, FR-18.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Milestone verified | email | 680×631 | [email.png](email.png) |
| 2 | Weekly report | email | 680×668 | [email-02-weekly-report.png](email-02-weekly-report.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Buttons, Status chip, Money display, Escrow trust line, Three-checks list, Checklist row, AI-generated label, Reviewed-by badge, Email template, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Review and approve", "Read the full report".

## 5. States and error cases

Designed states: Milestone verified; Weekly report.

## 6. Business rules the UI must enforce

- Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.

## 7. Responsive and accessibility notes

- Designed variants: email (2).
- Single column, 600–680px; live text, not images; button is a real link; works in dark-mode clients.

## 8. Open questions

- Only two client emails were designed; dispute and released emails reuse this layout (not designed).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
