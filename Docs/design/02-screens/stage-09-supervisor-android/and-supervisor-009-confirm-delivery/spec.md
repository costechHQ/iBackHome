---
id: AND-SUPERVISOR-009
title: "Confirm delivery"
stage: 9
surface: android
role: supervisor
priority: P1
fr: ["FR-16"]
route: "DeliveryScreen"
suggested_target: "mobile/lib/features/deliveries/ (new folder; not in the Spec)"
api: ["POST /orders/{id}/delivery", "POST /evidence/upload-url", "POST /evidence"]
links_to: []
states: ["default", "delivery-to-confirm-fri-18-dec-12-15", "count-and-photograph", "delivery-confirmed", "loading", "error"]
inventory_refs: ["SV-13"]
missing_endpoints: ["MX-05"]
source_boards: ["Sup-Delivery.dc.html"]
---

# AND-SUPERVISOR-009 · Confirm delivery

## 1. Purpose

Count delivered materials, photograph them in-app and confirm, which lets the supplier be paid.

From the approved board (`Sup-Delivery.dc.html`): "The supervisor is the only person who can confirm a delivery: a count for each line, with a photo that passes the same three checks. His confirmation triggers the supplier payment from the milestone escrow. Order O-0141, as the client saw it in Stage 7."

Stage 1 inventory: SV-13. Priority P1 · FRs FR-16.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Delivery to confirm · Fri 18 Dec, 12:15 | android | 360×800 | [android.png](android.png) |
| 2 | Count and photograph | android | 360×800 | [android-02-count-and-photograph.png](android-02-count-and-photograph.png) |
| 3 | Delivery confirmed | android | 360×800 | [android-03-delivery-confirmed.png](android-03-delivery-confirmed.png) |

Components (see [components.md](../../../01-design-system/components.md)): Android app bar and bottom nav, Buttons, Status chip, Alert and banner, Escrow trust line, Evidence card, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Delivery count | deliveries.quantities, deliveries.evidence_ids, confirmed_by, confirmed_at |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Start counting", "Photo", "Confirm delivery", "Done".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /orders/{id}/delivery`
- `POST /evidence/upload-url`
- `POST /evidence`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-05: Material order reads

## 5. States and error cases

Designed states: Delivery to confirm · Fri 18 Dec, 12:15; Count and photograph; Delivery confirmed.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in AND-SUPERVISOR-016 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- A supplier is paid directly only after the supervisor confirms the delivery on site.
- Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.

## 7. Responsive and accessibility notes

- Designed variants: android (3).
- Touch targets at least 48dp; body text 15/22 minimum; supports system font scaling to 130%.
- TalkBack labels on icon buttons; status announced in text, not colour alone.
- Works one-handed on a 360×800 screen; primary action in the bottom area.

## 8. Open questions

- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-05: List a project's orders, read one order, list a supplier's own orders, put payment on hold or cancel. The Spec has create, approve and delivery only.
