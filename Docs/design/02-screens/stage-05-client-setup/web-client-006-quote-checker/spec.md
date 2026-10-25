---
id: WEB-CLIENT-006
title: "Quote checker"
stage: 5
surface: web
role: client
priority: P0
fr: ["FR-17", "FR-05"]
route: "/projects/:id/boq/check"
suggested_target: "web/src/features/projects/ (calls quotes/check) "
api: ["POST /quotes/check", "GET /price-index", "GET /projects/{id}/boq"]
links_to: ["WEB-CLIENT-020"]
states: ["default", "1-choose-what-to-check", "2-checking", "3-results-flagged-lines-first", "4-price-index-reference", "results", "loading", "error"]
inventory_refs: ["CS-07"]
missing_endpoints: []
source_boards: ["Setup-Quote.dc.html"]
---

# WEB-CLIENT-006 · Quote checker

## 1. Purpose

Run the AI quote checker on the BoQ or an uploaded quote PDF and show flagged lines first, with the index price and % difference.

From the approved board (`Setup-Quote.dc.html`): "AI reads the quote into line items; plain rules compare each unit price with the price index and each quantity with the expected range for the house plan. Lines more than 15% above the index are flagged. It's advisory only — the client and ops decide. Prices shown are sample data."

Stage 1 inventory: CS-07. Priority P0 · FRs FR-17, FR-05.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | 1 · Choose what to check | desktop | 1280×800 | [desktop.png](desktop.png) |
| 2 | 2 · Checking | desktop | 1280×800 | [desktop-02-2-checking.png](desktop-02-2-checking.png) |
| 3 | 3 · Results — flagged lines first | desktop | 1280×800 | [desktop-03-3-results-flagged-lines-first.png](desktop-03-3-results-flagged-lines-first.png) |
| 4 | 4 · Price index reference | desktop | 1280×800 | [desktop-04-4-price-index-reference.png](desktop-04-4-price-index-reference.png) |
| 5 | Results | mobile | 390×844 | [mobile.png](mobile.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Buttons, Status chip, Skeleton loader, Quote check result, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Flagged lines | POST /quotes/check result: item, quantity, unit price, index price, % difference, reason |
| Index date | price_index_entries.observed_on |
| Index rows | GET /price-index -> item, unit, price_minor, currency, supplier_name, observed_on, source |
| Stale flag | observed_on older than 14 days (price_index.stale_check) |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Run the check", "Flagged · 3", "Within range · 58", "Not in index · 3", "Send back with these notes", "Back to the BoQ".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /quotes/check`
- `GET /price-index`
- `GET /projects/{id}/boq`

Navigates to: WEB-CLIENT-020.

## 5. States and error cases

Designed states: 1 · Choose what to check; 2 · Checking; 3 · Results — flagged lines first; 4 · Price index reference; Results.

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.

## 7. Responsive and accessibility notes

- Designed variants: desktop (4), mobile (1).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Quote PDF upload on the web is allowed (it is not evidence); the Spec does not say how the PDF reaches POST /quotes/check.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
