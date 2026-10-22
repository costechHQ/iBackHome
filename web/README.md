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
