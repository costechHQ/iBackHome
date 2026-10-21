# Build order

Recommended order for building the approved screens into the existing repo. Follow it one stage at a time; after each stage run the project's lint, type-check and tests (Spec CI: `ruff`, `mypy`, `eslint` + `prettier`, `tsc`, `dart analyze`, test suites) and tick the stage's items in [acceptance-checklist.md](acceptance-checklist.md).

Dependencies: the Spec builds base modules (users/OTP, payments, notifications, geo, audit) first. Screens that need an endpoint that does not exist yet are built against mock adapters (see ../04-api-mapping/missing-endpoints.md) and switched to the generated API client when the endpoint lands.

## Stage 0 · Inspect the repo (no code)

Read the existing `web/`, `mobile/` and `backend/` structure, the generated API clients (from FastAPI's OpenAPI at `/docs`), routing, state management, the UI kit in `web/src/common/` and any Flutter widgets in `mobile/lib/core/`. Write down where each item below will live. Adapt this package to the repo's conventions.

## Stage 1 · Shared: design-system layer

1. Web: add tokens (`01-design-system/tokens.css` as CSS variables, or `tailwind.tokens.ts` if Tailwind is used), fonts (`05-assets/fonts.md`), focus ring, tabular numbers.
2. Android: add `flutter_theme.dart` (`IbhColors`, `IbhText`, `ibhTheme()`), fonts, 48dp targets.
3. Build the shared components in [components.md](../01-design-system/components.md) once: buttons, inputs, OTP input, status chip (one source of truth for state → label/tone from [state-to-ui.md](../04-api-mapping/state-to-ui.md)), alert, toast/snackbar, skeleton, empty state, error page, dialog/alert dialog, bottom sheet, money display, escrow trust line, AI-generated label, three-checks list, evidence card, milestone stepper, geofence map, table, card, avatar.
4. Build the app shells: client top bar + project tabs + mobile bottom nav; contractor top bar; supplier bar; ops sidebar; Android app bar + bottom nav; the shared system states (WEB-CLIENT-024, AND-SUPERVISOR-016) and empty states.

## Stage 2 · Vertical slice: milestone release (end to end)

Build these first, against the real endpoints (`claim`, `verify`, `approve`, `ledger`, `milestones`, `evidence`) and the simulated escrow, before anything else:

| Order | Screen | Platform |
|---|---|---|
| 1 | AND-CONTRACTOR-002 Projects and claim (Android) / WEB-CONTRACTOR-005 Milestones and claim (web) | Flutter / React |
| 2 | AND-SUPERVISOR-005 Arrival check → AND-SUPERVISOR-006 Capture → AND-SUPERVISOR-007 Sync queue | Flutter (offline queue, Keystore signing, no gallery) |
| 3 | AND-SUPERVISOR-008 Verify or send back | Flutter |
| 4 | WEB-CLIENT-013 Milestone detail (all six states) | React |
| 5 | WEB-CLIENT-014 Approve a release (3 taps on mobile web) + receipt | React |
| 6 | WEB-CLIENT-015 Raise a dispute + WEB-OPS-006 ops two-approver resolution | React |
| 7 | WEB-CLIENT-017 Ledger | React |

Done when the Spec's end-to-end test (fund → capture → claim → verify → approve → release) passes on staging with these screens, and the dual-approval rule cannot be bypassed from any UI. Prototype B in 03-prototype-flows is the reference.

## Stage 3 · Auth and onboarding

Web: WEB-PUBLIC-010, WEB-CONTRACTOR-001, WEB-CLIENT-001, WEB-CONTRACTOR-002, WEB-SUPPLIER-001, WEB-OPS-001, WEB-CLIENT-002
Android: AND-PUBLIC-001, AND-SUPERVISOR-001, AND-SUPERVISOR-002, AND-CONTRACTOR-001

## Stage 4 · Client set-up and dashboard (web)

WEB-CLIENT-003, WEB-CLIENT-004, WEB-CLIENT-005, WEB-CLIENT-006, WEB-CLIENT-007, WEB-CLIENT-008, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-016, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020

## Stage 5 · Contractor (web, then Android)

Web: WEB-CONTRACTOR-003, WEB-CONTRACTOR-004, WEB-CONTRACTOR-005, WEB-CONTRACTOR-006, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009
Android: AND-CONTRACTOR-002, AND-CONTRACTOR-003, AND-CONTRACTOR-004, AND-CONTRACTOR-005

## Stage 6 · Supervisor app (rest of Android)

AND-SUPERVISOR-004, AND-SUPERVISOR-005, AND-SUPERVISOR-006, AND-SUPERVISOR-007, AND-SUPERVISOR-008, AND-SUPERVISOR-009, AND-SUPERVISOR-010, AND-SUPERVISOR-011, AND-SUPERVISOR-012

## Stage 7 · Ops console (desktop)

WEB-OPS-001, WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012, WEB-OPS-013, WEB-OPS-014

## Stage 8 · Supplier portal and materials flow (P1)

WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-004, WEB-SUPPLIER-005, WEB-SUPPLIER-006, WEB-SUPPLIER-007, WA-SUPPLIER-001, plus the client/contractor order screens if not done (WEB-CLIENT-019, WEB-CONTRACTOR-007).

## Stage 9 · Messages, notifications and settings

Templates in `backend/app/base/notifications/` (submit WhatsApp templates to Meta early): WA-CLIENT-001, AND-SUPERVISOR-013, EMAIL-CLIENT-001, AND-SUPERVISOR-014, AND-CONTRACTOR-006, WA-CLIENT-002. Settings: WEB-CLIENT-023, WEB-CONTRACTOR-010, WEB-OPS-013, AND-SUPERVISOR-015, WEB-SUPPLIER-008.

## Stage 10 · Public site and P2 placeholders

WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009, WEB-PUBLIC-010. P2 placeholders only: WEB-CLIENT-021, WEB-CLIENT-022.

## Parallel tracks

- Android and web can run in parallel after Stage 1; the vertical slice needs both.
- Backend gaps (missing-endpoints.md) should be raised during Stage 0 so the backend owner can schedule them; P0 screens blocked by a gap: MX-07 (evidence detail checks), MX-20 (escrow balance), MX-10 (dispute reads), MX-21 (money alerts).
