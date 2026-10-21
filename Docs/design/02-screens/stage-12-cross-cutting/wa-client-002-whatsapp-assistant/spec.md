---
id: WA-CLIENT-002
title: "WhatsApp assistant"
stage: 12
surface: whatsapp
role: client
priority: P1
fr: ["FR-20"]
route: "webhook: POST /webhooks/whatsapp"
suggested_target: "backend/app/features/agents/"
api: ["POST /webhooks/whatsapp"]
links_to: []
states: ["default", "whatsapp-assistant-questions-it-answers", "read-only-boundary-hand-off-to-ops", "loading", "error"]
inventory_refs: ["CM-11"]
missing_endpoints: []
source_boards: ["X-Assistant.dc.html"]
---

# WA-CLIENT-002 · WhatsApp assistant

## 1. Purpose

Questions the assistant answers from the client's own project data, and the read-only boundary with hand-off to ops.

From the approved board (`X-Assistant.dc.html`): "A read-only AI that answers "how far" and "how much" from the client's own data, and hands off to a person as soon as a conversation turns into a complaint or a dispute."

Stage 1 inventory: CM-11. Priority P1 · FRs FR-20.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | WhatsApp assistant · questions it answers | whatsapp | 390×844 | [whatsapp.png](whatsapp.png) |
| 2 | Read-only boundary · hand-off to ops | whatsapp | 390×844 | [whatsapp-02-read-only-boundary-hand-off-to-ops.png](whatsapp-02-read-only-boundary-hand-off-to-ops.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Money display, Escrow trust line, Evidence card, WhatsApp message, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /webhooks/whatsapp`

## 5. States and error cases

Designed states: WhatsApp assistant · questions it answers; Read-only boundary · hand-off to ops.

## 6. Business rules the UI must enforce

- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."

Designer note on the board (`X-Assistant.dc.html`), **What the assistant can and can't do**:

> Can: answer from this client's own projects only: progress, milestones, money from the ledger, the latest report, with a dashboard link.
> Can't: approve, release, fund, raise a dispute for you, change anything, or give opinions on the work.
> Hands off to ops on complaints, disputes, anything about money going wrong, or when it isn't sure. The chat then shows a named person.
> Every answer carries the "AI assistant" label, and every run is logged with its tool calls in the ops console.

## 7. Responsive and accessibility notes

- Designed variants: whatsapp (2).
- Plain text that reads well without buttons; buttons are template quick replies or URL buttons.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[2 business hours]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
