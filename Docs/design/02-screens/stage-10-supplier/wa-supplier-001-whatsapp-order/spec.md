---
id: WA-SUPPLIER-001
title: "WhatsApp order notification"
stage: 10
surface: whatsapp
role: supplier
priority: P1
fr: ["FR-16", "FR-20"]
route: "template: supplier_new_order, supplier_paid"
suggested_target: "backend/app/base/notifications/ (templates)"
api: []
links_to: []
states: ["default", "whatsapp-chat-mock", "loading", "error"]
inventory_refs: ["SU-05"]
missing_endpoints: []
source_boards: ["Sp-WhatsApp.dc.html"]
---

# WA-SUPPLIER-001 · WhatsApp order notification

## 1. Purpose

WhatsApp messages a supplier gets for a new order and payment.

From the approved board (`Sp-WhatsApp.dc.html`): "A mock of what the supplier receives on WhatsApp: a short, factual message with one button that opens the order in the portal. It's shown in a neutral chat layout, not WhatsApp's own branding."

Stage 1 inventory: SU-05. Priority P1 · FRs FR-16, FR-20.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | WhatsApp chat (mock) | whatsapp | 390×844 | [whatsapp.png](whatsapp.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Escrow trust line, Ledger row and receipt, WhatsApp message.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

## 5. States and error cases

Designed states: WhatsApp chat (mock).

## 6. Business rules the UI must enforce

- Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.
- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.

Designer note on the board (`Sp-WhatsApp.dc.html`), **Message template: supplier_order_approved**:

> Sent through the WhatsApp Business API. Messages outside the 24-hour window must use a template Meta has approved, so this one is submitted in week one.
> New order: [1]
> [2], [3].
> [4] · [5] · deliver by [6].
> You're paid directly after the supervisor confirms delivery.
> Button: View order → [7]
> [1] order number · [2] project · [3] area · [4] short item list · [5] total in naira · [6] deliver-by date · [7] link to the order
> Never in a message: the client's name or phone, bank numbers, or login codes. If WhatsApp fails, the same message goes by SMS, then email.

## 7. Responsive and accessibility notes

- Designed variants: whatsapp (1).
- Plain text that reads well without buttons; buttons are template quick replies or URL buttons.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
