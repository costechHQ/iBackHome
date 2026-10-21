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
bun run dev                 # http://127.0.0.1:3000
bun run lint                # eslint
bun run format:check        # prettier (bun run format to fix)
bun run typecheck           # tsc
bun run test                # vitest
bun run build && bun run e2e   # Playwright against next start (first time: bun x playwright install chromium)
bun run gen:api             # regenerate src/common/api/ from the backend's OpenAPI (needs uv)
```

Regenerate the API client whenever a backend route or schema changes, and commit both files in `src/common/api/`; CI fails if they differ from the backend (`api-contract` workflow).

With Docker: `docker compose up --build` from the repo root also starts `web` on http://127.0.0.1:3000.
