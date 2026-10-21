---
id: WEB-CLIENT-024
title: "System states (web)"
stage: 12
surface: web
role: client
priority: P0
fr: ["FR-01"]
route: "(shared states for every web portal)"
suggested_target: "web/src/common/ (UI kit: error pages, toasts, dialogs, skeletons)"
api: []
links_to: []
states: ["default", "404-page-not-found", "500-server-error", "permission-denied-403", "409-conflict-already-done-elsewhere", "form-validation", "session-expired", "offline", "loading-skeleton", "success-toasts", "confirmation-dialog", "destructive-dialog", "loading", "error"]
inventory_refs: ["NS-10"]
missing_endpoints: []
source_boards: ["X-StatesWeb.dc.html"]
---

# WEB-CLIENT-024 · System states (web)

## 1. Purpose

404, 500, 403, 409 conflict, form validation, session expired, offline, loading skeleton, toasts, confirmation and destructive dialogs. Shown in the client portal; every portal uses the same patterns.

From the approved board (`X-StatesWeb.dc.html`): "The shared states every web portal uses: errors, conflicts, validation, session and offline handling, loading, toasts and dialogs. Shown in the client portal; contractor, supplier and ops use the same patterns with their own top bar."

Stage 1 inventory: NS-10. Priority P0 · FRs FR-01.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | 404 · page not found | desktop | 960×600 | [desktop.png](desktop.png) |
| 2 | 500 · server error | desktop | 960×600 | [desktop-02-500-server-error.png](desktop-02-500-server-error.png) |
| 3 | Permission denied · 403 | desktop | 960×600 | [desktop-03-permission-denied-403.png](desktop-03-permission-denied-403.png) |
| 4 | 409 · conflict, already done elsewhere | desktop | 960×600 | [desktop-04-409-conflict-already-done-elsewhere.png](desktop-04-409-conflict-already-done-elsewhere.png) |
| 5 | Form validation | desktop | 960×600 | [desktop-05-form-validation.png](desktop-05-form-validation.png) |
| 6 | Session expired | desktop | 960×600 | [desktop-06-session-expired.png](desktop-06-session-expired.png) |
| 7 | Offline | desktop | 960×600 | [desktop-07-offline.png](desktop-07-offline.png) |
| 8 | Loading skeleton | desktop | 960×600 | [desktop-08-loading-skeleton.png](desktop-08-loading-skeleton.png) |
| 9 | Success toasts | desktop | 960×600 | [desktop-09-success-toasts.png](desktop-09-success-toasts.png) |
| 10 | Confirmation dialog | desktop | 960×600 | [desktop-10-confirmation-dialog.png](desktop-10-confirmation-dialog.png) |
| 11 | Destructive dialog | desktop | 960×600 | [desktop-11-destructive-dialog.png](desktop-11-destructive-dialog.png) |

Components (see [components.md](../../../01-design-system/components.md)): Wordmark, Client top bar, Buttons, Text input and select, Status chip, Alert and banner, Toast and snackbar, Skeleton loader, Error page, Dialog and alert dialog, Money display, Escrow trust line, Ledger row and receipt, Card, Avatar (initials).

## 3. Data shown

No API data. Copy is static (see `screen.html`); fixtures.json says so.

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Go to my projects", "Help centre", "Try again", "Contact us", "Go to my payouts", "Back", "See release status", "Back to project", "Continue", "Review and approve", "Cancel", "Approve order", "Keep invitation", "Cancel invitation".

## 5. States and error cases

Designed states: 404 · page not found; 500 · server error; Permission denied · 403; 409 · conflict, already done elsewhere; Form validation; Session expired; Offline; Loading skeleton; Success toasts; Confirmation dialog; Destructive dialog.

Error codes handled here (see [error-codes-to-ui.md](../../../04-api-mapping/error-codes-to-ui.md)): `conflict_409`.

## 6. Business rules the UI must enforce

- Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.
- Status colour appears only in chips and alerts, and every state also differs by text or shape.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Every write sends an Idempotency-Key; disable the submit button while a write is in flight.

Designer note on the board (`X-StatesWeb.dc.html`), **Rules across the web states**:

> Every error says what happened, whether money was affected, and what to do next. Never just a code.
> Destructive buttons are red and appear only inside a dialog. The safe choice is on the left and named for what it keeps.
> Focus moves into each dialog and returns to the button that opened it. Escape closes everything except an alertdialog about money.
> Error colour sits only in alerts, field borders and helper text.

## 7. Responsive and accessibility notes

- Designed variants: desktop (11).
- No mobile frame was designed; follow the mobile pattern of the same portal (single column, bottom nav, full-width primary button).
- Client approvals must work in under 3 taps on mobile web (FR-15).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- PLACEHOLDER values on this screen (in square brackets on the design): `[12 hours]`, `[10 s]`.
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
