# iBackHome · design handoff package

The approved iBackHome designs (Stages 1–13 on the Design canvas) packaged for two readers:

1. **Claude Code**, which will build these screens into the existing iBackHome repo (FastAPI backend, React + TypeScript + Vite web, Flutter Android app, as in the Spec). Start at [CLAUDE.md](CLAUDE.md).
2. **A human reviewer** who wants to browse the designs without any tooling. Open [index.html](index.html).

Nothing here was redesigned. Every screen is a static export of an approved board; where something was missing or inconsistent it is recorded in [PACKAGE-REPORT.md](PACKAGE-REPORT.md), not fixed by invention.

**98 screens** (P0 59 · P1 37 · P2 2 placeholders) · **296 designed states** with screenshots · 5 clickable prototype flows · FR-01 to FR-23 traced.

## How to browse (no tooling)

1. Unzip and open `index.html` in any modern browser. It works offline: fonts and styles are bundled.
2. Filter by role, surface or priority, or search by ID, title or FR.
3. Click a thumbnail to open that screen's `screen.html`, which shows **every designed state** of the screen, at real size, in static HTML.
4. Open `spec.md` next to it for purpose, data mapping, rules, states and open questions (any Markdown viewer, or GitHub).
5. For journeys, open the click-throughs in `03-prototype-flows/` (Next/Back, or click the main button).
6. For the visual component sheet, open `01-design-system/components.html`.

## Folder map

| Path | What it is |
|---|---|
| `README.md` | This file |
| `CLAUDE.md` | Instructions for Claude Code: read order, stack, rules, working method, do-nots |
| `index.html` | Offline gallery of every screen, grouped by stage and role |
| `manifest.json` | Machine-readable index: one object per screen (id, title, stage, surface, role, priority, fr, route, suggested_target, api, html, screenshots, spec, fixtures, plus states, links, gaps) |
| `PACKAGE-REPORT.md` | Verification results, gaps, assumptions, placeholders, items not designed, inconsistencies |
| `00-overview/` | Product summary, screen inventory, flows (Mermaid), requirements traceability |
| `01-design-system/` | Tokens (JSON, CSS variables, Tailwind theme, Flutter theme), components (list + visual sheet), icons |
| `02-screens/stage-NN-…/<screen-id>-<slug>/` | One folder per screen: `screen.html`, screenshots, `spec.md`, `fixtures.json` |
| `03-prototype-flows/` | Stage 13 prototypes A–E as offline click-throughs, with screen IDs per step |
| `04-api-mapping/` | Screen → endpoint, state → UI, error codes → UI, missing endpoints |
| `05-assets/` | Logo SVGs, fonts (WOFF2 + licences) and font notes, images note |
| `06-build-plan/` | Build order and per-screen acceptance checklist |

Screens per stage: 3 · Public site (9), 4 · Auth and onboarding (13), 5 · Client project setup (5), 6 · Client dashboard and evidence (5), 7 · Client milestones, money, reports, orders (10), 8 · Contractor (11), 9 · Supervisor Android app (9), 10 · Supplier portal (7), 11 · Ops console (11), 12 · Cross-cutting: messages, settings, system states (18).

## Screen IDs

`<SURFACE>-<ROLE>-<NNN>`, for example `WEB-CLIENT-014` (Approve a release). SURFACE is `WEB` (desktop and mobile web; spec surface `web` or `mobile-web`), `AND` (Flutter Android), `WA` (WhatsApp template) or `EMAIL`. ROLE is `PUBLIC`, `CLIENT`, `CONTRACTOR`, `SUPERVISOR`, `SUPPLIER` or `OPS`. IDs are stable across the inventory, manifest, folders, specs, traceability and prototype flows. Each spec also lists its Stage 1 inventory IDs (`inventory_refs`).

## Screenshot names

`desktop.png` (1280 or 1440 wide; 960 for the shared web system states), `mobile.png` (390), `android.png` (360×800), `whatsapp.png` (390 phone mock), `email.png` (680), `card.png` (480 sign-in card), `panel.png`, `tile.png` (empty-state tile). The first frame of each variant takes the plain name; further states are `<variant>-NN-<state>.png`. Only variants that were designed exist. Screenshots are 1× renders of the approved boards (256-colour PNG).

## How to hand this to Claude Code

1. Copy the unzipped `ibackhome-design-handoff/` folder into the repo, for example at `docs/design-handoff/` (keep it out of the build).
2. Open Claude Code in the repo root and say:

   > Read `docs/design-handoff/CLAUDE.md` and follow it. Start with Stage 0 in `docs/design-handoff/06-build-plan/build-order.md`: inspect the repo and tell me where each layer will go before writing code.

3. Review stage by stage. Each stage ends with lint, type-check and tests green and the acceptance checklist updated.

## Source of truth

The Design canvas (private artifact) and the PRD and Spec remain the source of truth. If this package and the canvas disagree, the canvas wins; if a design and the Spec disagree on a rule, see the conflicts section of PACKAGE-REPORT.md.
