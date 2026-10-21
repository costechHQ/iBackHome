---
id: WA-CLIENT-001
title: "Client WhatsApp messages"
stage: 12
surface: whatsapp
role: client
priority: P1
fr: ["FR-20", "FR-18"]
route: "templates: milestone_claimed, milestone_verified, release_completed, weekly_report_ready"
suggested_target: "backend/app/base/notifications/ (templates)"
api: []
links_to: []
states: ["default", "client-whatsapp-chioma", "client-whatsapp-weekly-report-summary", "loading", "error"]
inventory_refs: ["NS-02", "CM-10"]
missing_endpoints: []
source_boards: ["X-Messages.dc.html"]
---

# WA-CLIENT-001 · Client WhatsApp messages

## 1. Purpose

Claimed, verified (approve to release), released and weekly report summary messages. Links open the web; nothing is approved in WhatsApp.

From the approved board (`X-Messages.dc.html`): "The five events from the notification table, as people actually receive them. The client gets WhatsApp. The spot check goes to the supervisor by push and SMS, because the spec routes it that way. Shown in a neutral chat layout, not WhatsApp's own branding."

Stage 1 inventory: NS-02, CM-10. Priority P1 · FRs FR-20, FR-18.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Client · WhatsApp · Chioma | whatsapp | 390×844 | [whatsapp.png](whatsapp.png) |
| 2 | Client · WhatsApp · weekly report summary | whatsapp | 390×844 | [whatsapp-02-client-whatsapp-weekly-report-summar.png](whatsapp-02-client-whatsapp-weekly-report-summar.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Money display, Escrow trust line, Ledger row and receipt, AI-generated label, Reviewed-by badge, WhatsApp message, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

## 5. States and error cases

Designed states: Client · WhatsApp · Chioma; Client · WhatsApp · weekly report summary.

## 6. Business rules the UI must enforce

- Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.

Designer note on the board (`X-Messages.dc.html`), **Message rules**:

> Every message says what happened, the money in both currencies when relevant, and one clear button.
> Messages sent outside WhatsApp's 24-hour window use Meta-approved templates. Each event above is one template.
> Never in a message: login codes (sent only on the channel asked for), full bank numbers, or another party's phone number.
> If WhatsApp fails, the same message goes by push, then SMS, then email, in the person's preferred order.

## 7. Responsive and accessibility notes

- Designed variants: whatsapp (2).
- Plain text that reads well without buttons; buttons are template quick replies or URL buttons.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
