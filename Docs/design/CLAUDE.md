# CLAUDE.md · building iBackHome from this design package

This folder is the approved design handoff for iBackHome (Stages 1–13, packaged in Stage 14). It contains 98 screens with static HTML, screenshots, specs and API-shaped fixtures, plus tokens, components, API mapping and a build plan. Your job is to **build these screens into the existing iBackHome repo**, not to redesign them and not to change the backend contract on your own.

## Read in this order

1. `README.md` (what is here, screen ID scheme)
2. `00-overview/` (product summary, screen inventory, flows, traceability)
3. `01-design-system/` (tokens, components, icons)
4. `04-api-mapping/` (screen → endpoint, state → UI, error codes → UI, missing endpoints)
5. `06-build-plan/` (build order, acceptance checklist)
6. Then the screens: `02-screens/<stage>/<screen>/spec.md`, with `screen.html` and the PNGs as the visual reference and `fixtures.json` as sample data. `manifest.json` indexes them.

`PACKAGE-REPORT.md` lists gaps, placeholders and conflicts; check it before building any screen it mentions.

## Target stack (from the Spec)

- **Web**: React + TypeScript, built with Vite (`web/src/common/` for the API client, auth, layout, map component and UI kit; `web/src/features/<feature>/`).
- **Android**: Flutter, Android 8+, 2 GB RAM, offline-first (`mobile/lib/core/`, `mobile/lib/features/<feature>/`).
- **Backend**: existing FastAPI REST API under `/api/v1`, OTP login returning a bearer JWT (15-minute access token, 30-day rotating refresh token), errors as `{"error": {"code", "message"}}`, `Idempotency-Key` on every write, `?cursor=&limit=` pagination. Web and mobile API clients are generated from the OpenAPI document at `/docs`.

**Inspect the existing repo first.** Before writing code, read its structure, conventions, generated API client, routing, state management, component library and theme setup. Adapt these designs to the repo's patterns, not the other way round. Each spec's `suggested_target` is only a suggestion following the Spec's folder layout; folders marked "new folder; not in the Spec" need a decision from the repo owner. Report your plan (where each layer goes) before the first code change.

## Rules

- **Tokens, never hard-coded colours.** Use `01-design-system/tokens.css` / `tailwind.tokens.ts` on the web and `flutter_theme.dart` on Android. The hex values inside `screen.html` are already mapped to `var(--ibh-*)`; any value left as raw hex is listed in PACKAGE-REPORT.md.
- **Reuse components** from `01-design-system/components.md`; build each once. Status chips take their label and tone from `04-api-mapping/state-to-ui.md`.
- **Build from the generated API client.** Never hand-write fetch calls to paths that bypass it.
- **Never invent endpoints.** Where a screen needs data the Spec does not provide (`missing_endpoints` in the spec front matter, `04-api-mapping/missing-endpoints.md`), use a mock adapter that returns the sample in that screen's `fixtures.json` → `mock_adapters`, keep it behind one clearly named module, and log the gap (PR description and acceptance checklist).
- **Money**: show the client's currency first (GBP, USD or EUR), then the NGN equivalent and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only. Money is integer minor units in the API; never use floats.
- **Escrow line**: wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- **Times**: stored in UTC; shown in the viewer's time zone (clients: their own zone, with UTC on hover where designed; Nigerian roles: WAT).
- **Supervisor (and contractor) app**: no gallery, file picker, share-in or any other path that accepts a file from device storage. In-app camera only (`camera` plugin; `image_picker` must not be a dependency). Refuse capture with GPS accuracy worse than 50 m or a mocked location.
- **Evidence**: show the same three checks (inside the site geofence, device-signed, not reused or edited) wherever evidence appears. Contractor uploads are labelled and never count toward verification. A flag never rejects a milestone by itself.
- **AI**: every AI-generated thing is labelled "AI-generated", cites the evidence IDs it used, and takes money figures from the ledger. No AI or agent path can approve, release, resolve or pay.
- **Release rule**: no UI action for agents and no UI shortcut that bypasses dual approval. A release needs supervisor verification AND client approval; a dispute pauses release; dispute resolution needs two different ops users. Approve buttons appear only in the states listed in `state-to-ui.md`.
- **States**: evidence states and milestone states (and every other state machine) exactly as in `04-api-mapping/state-to-ui.md`; handle 409 as a designed conflict state, not a generic error.
- **Accessibility**: WCAG AA: 4.5:1 text, visible focus, real buttons/links/labels, dialogs that trap and return focus, 44px web / 48dp Android targets, status never by colour alone.

## Working method

1. **One stage at a time**, in the order of `06-build-plan/build-order.md`.
2. **Design-system layer first**: tokens, themes, fonts, then the shared components and app shells.
3. **Then one vertical slice end to end: the milestone release flow** (claim → capture → sync → verify → approve → release, plus the dispute path), on web and Android, against the real endpoints and the simulated escrow, before any other screen. Prototype B (`03-prototype-flows/flow-b-claim-to-release.html`) is the reference.
4. Then the remaining screens, stage by stage.
5. **After each stage**: run the project's lint, type-check and tests (Spec CI: `ruff`, `mypy`, `eslint`, `prettier`, `tsc`, `dart analyze`, test suites), fix failures, and tick the stage's items in `06-build-plan/acceptance-checklist.md` (copy it into the repo's docs if you prefer; keep the IDs).
6. Compare each built screen with its `screen.html` and PNGs at the designed widths (1280/1440 desktop, 390 mobile web, 360×800 Android). Match layout, copy and states; do not add UI that isn't designed.
7. When a spec and the Spec disagree, the Spec wins for behaviour unless PACKAGE-REPORT.md says the decision is pending; then make it configurable, default to the Spec, and flag it.

## Do not

- Do not copy placeholder pricing, sample names (Chioma, Engr. Obi, Ifeanyi …), sample amounts, rates, dates, IDs or fixture data into production code, seed data for production, or copy strings that ship. Anything marked PLACEHOLDER or in [square brackets] needs a real value from the product owner.
- Do not add features outside the PRD and the Spec, even if a design hints at one. If a design element needs a backend change, log it as a gap.
- Do not implement P2 screens beyond their placeholders (`WEB-CLIENT-021` live walkthrough, `WEB-CLIENT-022` land and title verification): no forms, bookings, prices or video SDK.
- Do not edit the backend API contract, money-moving code (`base/payments`, `features/escrow`) or the state machines to fit a design.
- Do not use the board-specific class names or inline styles in `screen.html` as production CSS; they are a visual reference. Build with the repo's components and the tokens.
