# web/

The web app: client dashboard, contractor and supplier portals, ops console. Owner: Gabriel.

Next.js (App Router) + TypeScript + Tailwind CSS, with a same-origin auth proxy (ADR 0003, `Docs/adr/0003-web-nextjs-bff.md`). The designs are in `Docs/design/` (screens `WEB-*`).

## Folders

- `src/app/`: routes only (pages, layouts, route handlers). No business logic; imports from `features/` and `common/`.
- `src/common/`: API client (`api/`, generated), auth, layout, map component, UI kit, theme. Shared by two or more features.
- `src/features/<feature>/`: auth, projects, dashboard, milestones, suppliers, reports, ops-console (the Spec's list).
- `e2e/`: Playwright tests. `scripts/`: dev scripts (not shipped).

ESLint stops `features/` and `common/` from importing `app/`, and `common/` from importing `features/`.

## Commands (Git Bash, from `web/`)

Bun is the package manager and script runner; Next itself runs on Node (22+).

```sh
bun install                 # exact versions from bun.lock
bun run dev -- --port 3010   # http://localhost:3010 (3000 is the Docker web service)
bun run lint                # eslint
bun run format:check        # prettier (bun run format to fix)
bun run typecheck           # tsc
bun run test                # vitest
bun run build && bun run e2e   # Playwright against next start on :3010 (first time: bun x playwright install chromium)
bun run gen:api             # regenerate src/common/api/ from the backend's OpenAPI (needs uv)
bun run sync:tokens         # copy the handoff's tokens.css and fonts into src/common/theme/
bun run gen:status          # regenerate the status chips from the handoff's state-to-ui.md
```

Regenerate the API client whenever a backend route or schema changes, and commit both files in `src/common/api/`; CI fails if they differ from the backend (`api-contract` workflow). The token copy and the status chips have drift tests too.

The web server calls the API at `API_INTERNAL_URL` (default `http://127.0.0.1:8000`, the Docker api). To sign in locally, start the Docker stack and use any phone or email: with `ENVIRONMENT=local` the code is in `docker compose logs api`. The backend allows 3 codes per number or email per 15 minutes.

`IBH_STACK=1 bun run e2e e2e/stack` also signs in through the real form against the local Docker API (skipped in CI). Add `IBH_STACK_SEEDED=1` when the database was seeded with `backend/scripts/seed.py` (the ops test signs in as the seeded ops user).

**States gallery (development only):** `IBH_DEV_PAGES=1 bun run dev -- --port 3010`, then http://localhost:3010/dev/states shows every shared state and shell, one frame per `?frame=`. It answers 404 without the variable, which Docker and staging never set. Playwright turns it on for its own server to run axe and take screenshots (`e2e/states.spec.ts`).

**UI rules in code:** colours, radii, shadows and type come only from the tokens (`bg-primary`, `rounded-card`, `type-h2`, ...). A test fails on any hex or rgb colour or Tailwind arbitrary value (`bg-[#...]`, `text-[13px]`) in `src/`. Shared components are in `src/common/ui/`, the portal shells in `src/common/layout/`; nav items appear once their screen is built (`nav.ts`, `ready`).

With Docker: `docker compose up --build` from the repo root also starts `web` on http://localhost:3000.

## Seed driver (local data in every milestone state)

The client screens need milestones in every state. The dev seed driver (`scripts/drive/`, never shipped) gets them there through the real API, as the people `backend/scripts/seed.py` creates. Local Docker Compose only.

```sh
# once, from the repo root: a clean database with people, projects and photos
docker compose up -d
docker compose exec api python scripts/seed.py
docker compose exec api python scripts/simulator.py --photos 2

# then from web/: one milestone into the state you need (prints its client URL)
bun scripts/drive/index.ts --to released --milestone 1 --project "3-bedroom bungalow, Trans-Ekulu"
bun scripts/drive/index.ts --to verified --milestone 2 --project "3-bedroom bungalow, Trans-Ekulu"
bun scripts/drive/index.ts --to disputed --milestone 1 --project "4-bedroom duplex, Independence Layout"
```

States: `funded`, `claimed`, `verified`, `approved`, `released`, `disputed`, `sent-back` (the supervisor rejects the claim with reasons). Funding sends the signed `checkout.session.completed` webhook Stripe would send, so it needs only `STRIPE_WEBHOOK_SECRET` in the repo's `.env` (any random value locally; no Stripe account). Captures are signed with an ECDSA P-256 key per SIGNING.md and pass the real checks (the worker must run). Tokens and device keys are kept in `web/.drive/` (gitignored).

Then `IBH_STACK=1 bun run e2e e2e/stack/client-release.spec.ts` checks every client screen against that data (axe at 1280 and 390 px, and a real approval in three taps). The backend allows 3 login codes per email per 15 minutes; the stack tests keep their browser session in `web/.drive/` between runs.

For the contractor and ops screens (W3), put one milestone into `sent-back` and another into `disputed`, then run `IBH_STACK=1 bun run e2e e2e/stack/contractor-ops.spec.ts`. It claims the sent-back milestone again as the contractor, and resolves the dispute for release as the two seeded ops users (one proposes, the other confirms), so run the driver again before the next run. The stack tests run one at a time because they share the database.

**Evidence photos locally:** the API signs photo URLs for the Docker host `storage:9000`, so a browser outside Docker can't load them. Add `127.0.0.1 storage` to your hosts file (`C:\Windows\System32\drivers\etc\hosts` on Windows, admin rights) to see them. Playwright maps the name itself. Staging uses R2's public URLs, so this is local only.

**Mock adapters:** `IBH_MOCKS=all` (set in both Compose files, never in production) turns on the mocks for missing endpoints in `src/common/api/mocks/` (MX-03, MX-10); without it the elements they fill are hidden. Add `IBH_MOCKS=all` when running `bun run dev`.
