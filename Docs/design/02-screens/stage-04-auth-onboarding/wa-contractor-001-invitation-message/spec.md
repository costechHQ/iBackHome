---
id: WA-CONTRACTOR-001
title: "Invitation message (WhatsApp)"
stage: 4
surface: whatsapp
role: contractor
priority: P0
fr: ["FR-03"]
route: "template: project_invitation"
suggested_target: "backend/app/base/notifications/ (template)"
api: []
links_to: []
states: ["default", "1-invitation-message-whatsapp-template", "loading", "error"]
inventory_refs: ["AU-05", "NS-01"]
missing_endpoints: ["MX-02"]
source_boards: ["Auth-Invite.dc.html"]
---

# WA-CONTRACTOR-001 · Invitation message (WhatsApp)

## 1. Purpose

WhatsApp template a contractor receives when a client invites them to a project.

From the approved board (`Auth-Invite.dc.html`): "Chioma invites Engr. Obi by phone. He gets a WhatsApp link, sees what he's joining, confirms with a code sent to the invited number, and lands in contractor onboarding. Mostly on a phone, so mobile first."

Stage 1 inventory: AU-05, NS-01. Priority P0 · FRs FR-03.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | 1 · Invitation message (WhatsApp template) | whatsapp | 390×844 | [whatsapp.png](whatsapp.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, WhatsApp message.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-02: Project invitations

## 5. States and error cases

Designed states: 1 · Invitation message (WhatsApp template).

## 6. Business rules the UI must enforce

- Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.

## 7. Responsive and accessibility notes

- Designed variants: whatsapp (1).
- Plain text that reads well without buttons; buttons are template quick replies or URL buttons.

## 8. Open questions

- Template must be submitted to Meta for approval in week one (Spec).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-02: View, accept, decline, resend and cancel an invitation (contractor by client; supplier and ops user by ops). The Spec only says POST /projects "invites contractor".
