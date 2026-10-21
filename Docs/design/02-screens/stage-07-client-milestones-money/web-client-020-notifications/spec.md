---
id: WEB-CLIENT-020
title: "Notifications"
stage: 7
surface: web
role: client
priority: P1
fr: ["FR-20"]
route: "/notifications"
suggested_target: "web/src/features/dashboard/ (no notifications feature on web in the Spec)"
api: []
links_to: ["WEB-CLIENT-013", "WEB-CLIENT-014", "WEB-CLIENT-018", "WEB-CLIENT-019"]
states: ["default", "desktop", "mobile-web", "loading", "error"]
inventory_refs: ["NS-02", "NS-03"]
missing_endpoints: ["MX-11"]
source_boards: ["Notifications.dc.html"]
---

# WEB-CLIENT-020 · Notifications

## 1. Purpose

In-app notification list with filters (needs action, money, milestones, reports) and links to the item.

From the approved board (`Notifications.dc.html`): "Everything we sent on WhatsApp, email or push, kept in one place across projects, with the channel it went out on. The bell in the top bar shows the unread count. Items that need a decision stay pinned to the top until they're done. Tue 15 Dec, 19:00 GMT."

Stage 1 inventory: NS-02, NS-03. Priority P1 · FRs FR-20.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Desktop | desktop | 1280×1080 | [desktop.png](desktop.png) |
| 2 | Mobile web | mobile | 390×1080 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Client bottom nav, Buttons, Status chip, Money display, Escrow trust line, Ledger row and receipt, AI-generated label, Reviewed-by badge, Quote check result, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Notification rows | notifications.template, payload, channel, sent_at: see MX-11 |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "All 8", "Needs action 1", "Money 3", "Milestones 3", "Reports 1", "Mark all as read", "Review order", "Mark all read".

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-11: In-app notification feed

Navigates to: WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-018, WEB-CLIENT-019.

## 5. States and error cases

Designed states: Desktop; Mobile web.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).

## 7. Responsive and accessibility notes

- Designed variants: desktop (1), mobile (1).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Stage 1 assumption G-25 said "no in-app inbox"; Stage 7 then designed this screen. It needs MX-11.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-11: List the signed-in user's notifications and mark them read (notifications table exists, no endpoint).
