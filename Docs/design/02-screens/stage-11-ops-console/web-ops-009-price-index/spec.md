---
id: WEB-OPS-009
title: "Price index management"
stage: 11
surface: web
role: ops
priority: P0
fr: ["FR-17"]
route: "/ops/price-index"
suggested_target: "web/src/features/ops-console/"
api: ["GET /price-index"]
links_to: []
states: ["default", "price-index-management", "loading", "error"]
inventory_refs: ["OP-13"]
missing_endpoints: ["MX-16"]
source_boards: ["Op-PriceIndex.dc.html"]
---

# WEB-OPS-009 · Price index management

## 1. Purpose

The index (15+ items with last-updated dates), stale items and pending supplier changes.

From the approved board (`Op-PriceIndex.dc.html`): "16 items from 5 partner suppliers, each with its source and last-updated date. Anything older than 14 days shows as stale everywhere the index appears. Price changes above [10%] wait for an ops check before they go live."

Stage 1 inventory: OP-13. Priority P0 · FRs FR-17.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Price index management | desktop | 1440×900 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Ops sidebar, Buttons, Text input and select, Segmented control and tabs, Search and filters, Status chip, Alert and banner, Quote check result, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Index rows | GET /price-index -> item, unit, price_minor, currency, supplier_name, observed_on, source |
| Stale flag | observed_on older than 14 days (price_index.stale_check) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Remind 2 suppliers", "Add item", "Accept change", "Reject".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /price-index`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-16: Price index writes

## 5. States and error cases

Designed states: Price index management.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Role and project membership decide what is visible (Spec, two-layer authorisation).

## 7. Responsive and accessibility notes

- Designed variants: desktop (1).
- Ops console is desktop only (1440 frames; minimum supported width 1280).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[10%]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-16: Ops add/edit index entries and approve supplier price changes; supplier submits its own prices. The Spec has GET /price-index only.
