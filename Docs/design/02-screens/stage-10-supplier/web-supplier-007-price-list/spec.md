---
id: WEB-SUPPLIER-007
title: "Price list contribution"
stage: 10
surface: web
role: supplier
priority: P1
fr: ["FR-17"]
route: "/s/prices"
suggested_target: "web/src/features/suppliers/ (price index)"
api: ["GET /price-index"]
links_to: ["WEB-SUPPLIER-002", "WEB-SUPPLIER-003", "WEB-SUPPLIER-005", "WEB-SUPPLIER-006"]
states: ["default", "mon-11-jan", "mobile-web", "loading", "error"]
inventory_refs: []
missing_endpoints: ["MX-16"]
source_boards: ["Sp-PriceList.dc.html"]
---

# WEB-SUPPLIER-007 · Price list contribution

## 1. Purpose

Supplier confirms or updates its own prices in the price index; stale items flagged after 14 days.

From the approved board (`Sp-PriceList.dc.html`): "Partner suppliers keep the price index current. Each price shows when it was last updated, and anything older than 14 days is marked stale. This is the same rule the client and contractor see as "Index updated Mon 4 Jan"."

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | Mon 11 Jan | desktop | 1280×860 | [desktop.png](desktop.png) |
| 2 | Mobile web | mobile | 390×844 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Supplier top bar and mobile nav, Buttons, Text input and select, Status chip, Alert and banner, Quote check result, Table, Card, Avatar (initials).

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Index rows | GET /price-index -> item, unit, price_minor, currency, supplier_name, observed_on, source |
| Stale flag | observed_on older than 14 days (price_index.stale_check) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Send updated prices", "Prices haven't changed".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `GET /price-index`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-16: Price index writes

Navigates to: WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-005, WEB-SUPPLIER-006.

## 5. States and error cases

Designed states: Mon 11 Jan; Mobile web.

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

- Not in the Stage 1 inventory; added in Stage 10. "Changes over [10%] checked by iBackHome first" threshold is PLACEHOLDER.
- PLACEHOLDER values on this screen (in square brackets on the design): `[10%]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-16: Ops add/edit index entries and approve supplier price changes; supplier submits its own prices. The Spec has GET /price-index only.
