---
id: WEB-PUBLIC-007
title: "Contact"
stage: 3
surface: web
role: public
priority: P1
fr: []
route: "/contact"
suggested_target: "web/src/features/public/ (new folder; the Spec lists no public-site feature)"
api: []
links_to: ["WEB-PUBLIC-001", "WEB-PUBLIC-002", "WEB-PUBLIC-003", "WEB-PUBLIC-004", "WEB-PUBLIC-005", "WEB-PUBLIC-006", "WEB-PUBLIC-008", "WEB-PUBLIC-009"]
states: ["default", "desktop", "pub-05b-contact", "loading", "error"]
inventory_refs: ["PUB-05"]
missing_endpoints: []
source_boards: ["SiteContact.dc.html", "SiteMobile.dc.html"]
---

# WEB-PUBLIC-007 · Contact

## 1. Purpose

Give visitors ways to reach the team.

From the approved board (`SiteContact.dc.html`): "Questions about a build, joining as a contractor or supervisor, or partnering with us. We'll get back to you within [RESPONSE TIME]."

From the approved board (`SiteMobile.dc.html`): "Verified supervisors capture site evidence that can't be faked. Your money waits with a licensed escrow partner and is released milestone by milestone — only when the work is confirmed and you approve."

Stage 1 inventory: PUB-05. Priority P1.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1440×1407 | [desktop.png](desktop.png) |
| 2 | PUB-05b · Contact | mobile | 390×2548 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Site header and footer, Buttons, Text input and select, Toggle, checkbox and radio card, Escrow trust line, Card.

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Get started", "Send message".

Navigates to: WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-008, WEB-PUBLIC-009.

## 5. States and error cases

Designed states: Desktop; PUB-05b · Contact.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Role and project membership decide what is visible (Spec, two-layer authorisation).

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Contact channels, phone numbers and addresses are PLACEHOLDER.
- The contact form has no endpoint in the Spec (not listed as an API gap because it may be a third-party form).
- PLACEHOLDER values on this screen (in square brackets on the design): `[RESPONSE TIME]`, `[WHATSAPP NUMBER]`, `[CONTACT EMAIL]`, `[OFFICE ADDRESS]`, `[OPENING HOURS]`, `[REGISTERED COMPANY NAME]`, `[NUMBER]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
