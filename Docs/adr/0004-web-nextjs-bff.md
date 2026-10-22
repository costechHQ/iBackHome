# ADR 0004: The web app is Next.js with a same-origin auth proxy

- **Status:** Accepted
- **Date:** 2026-10-21
- **Owner:** Gabriel
- **Supersedes:** the "React + TypeScript (Vite)" web choice in `Docs/spec.md` (Overview)
- **Spec edits:** commit `docs: update spec for Next.js web app`. It changes the Overview Web row, adds `app/` to the web code tree with its rule, adds a cookie note under Auth, adds `web` to the local environment, adds the web build and tests to CI, extends decision 3 (hosting), and adds decision 9.

## Context

The web app is built from the approved design handoff in `Docs/design/`. It needs a public site that is fast and statically rendered, signed-in screens for four roles, and login that is safe for a product holding other people's money. The backend gives a 15-minute access JWT and a 30-day refresh token. The refresh token rotates once, and reusing one revokes every session of that user, so the token must not be stolen and a refresh must never be retried blindly. A browser SPA would keep both tokens where page JavaScript can read them.

## Decision

**Framework**

- Next.js (App Router), TypeScript strict, Tailwind CSS v4. React stays, so the PRD's "React web" is still accurate.
- Bun is the package manager and script runner only. Next runs on Node, in the container too. Versions are pinned exactly in `web/package.json` and `web/bun.lock`.

**Folders**

- `web/src/common/` and `web/src/features/` are exactly the Spec's folders, with the same rule that code used by two or more features goes in `common/`.
- The only addition is `web/src/app/`, the routing layer Next.js requires. Route files (page, layout, loading, error, not-found, route handlers) hold no business logic and only import from `features/` and `common/`. `features/` and `common/` never import from `app/`, and `common/` never imports from `features/`. ESLint enforces these rules.
- There is one route group per audience, `(public)`, `(auth)`, `(client)`, `(contractor)` and `(ops)`, each with its own layout and role shell.

**Auth: backend-for-frontend (BFF)**

- Next route handlers do the OTP exchange with FastAPI and store the access and refresh tokens in httpOnly, secure, SameSite cookies. Browser JavaScript never sees a token.
- A same-origin proxy under `/api/v1/*` forwards the browser's calls to FastAPI with `Authorization: Bearer <access token>` taken from the cookie. Because everything is same-origin, the backend needs no CORS changes. The proxy also forwards the caller's IP in `X-Forwarded-For`, so the backend's per-IP OTP limit still counts real callers.
- Server-only auth and proxy code lives in `web/src/common/auth/` and `web/src/common/api/`, marked `server-only`. The route handlers under `app/api/` only call it.
- **Refresh is single-flight on the server.** Concurrent requests for the same session share one in-flight refresh promise, keyed by the refresh token, and a refresh is never retried blindly. If it fails, the session ends and the user signs in again. The lock is in memory, which is correct for the single web container on the staging VPS. **If we ever run more than one web instance, it must become a shared lock** (for example in Redis); otherwise two instances can spend the same refresh token and revoke the user's sessions.
- **Role guards:** `src/proxy.ts`, Next 16's name for middleware, only checks that a session cookie exists. Each route-group layout reads the role from `GET /me` on the server. The backend stays the real authority on every request.
- Mobile is unchanged: bearer tokens in Android encrypted storage, calling FastAPI directly.

**API client and errors**

- The client is generated from FastAPI's OpenAPI document. `web/scripts/gen-api.sh` writes `web/src/common/api/openapi.json` and `schema.d.ts` (openapi-typescript), and requests go through openapi-fetch. CI regenerates both and fails on any difference (`api-contract` workflow).
- Every write action gets one `Idempotency-Key`, kept across that action's retries.
- Errors are parsed as `{"error": {"code", "message"}}` and mapped through `Docs/design/04-api-mapping/error-codes-to-ui.md`. A 409 is a designed conflict state, not an error boundary.
- Where the backend lacks an endpoint a screen needs, a mock adapter in `web/src/common/api/mocks/` sits behind a per-gap flag. Each one is logged in `Docs/design/04-api-mapping/missing-endpoints.md` as a proposal for the backend owner.

**Caching and rendering**

- Public pages (landing, how it works, pricing and so on) are server components, rendered statically.
- Signed-in screens are rendered dynamically and are mostly client components using TanStack Query.
- Signed-in routes and the proxy send `Cache-Control: no-store` and are never cached by Next. Nothing that contains money or evidence is statically rendered or cached.
- Evidence images are private signed URLs that expire after 15 minutes. They are shown with a plain `<img>` (fixed size, lazy loading), never through `next/image`'s optimiser, which would fetch and cache them on the server. `next/image` is used only for our own static assets.

**UI**

- `Docs/design/01-design-system/tokens.css` is the single source of design values. It is copied into `web/src/common/theme/` and mapped into Tailwind with an `@theme inline` block that refers to the CSS variables. No hex values and no arbitrary-value colour classes appear in components.
- Variants use class-variance-authority, clsx and tailwind-merge. Accessible primitives come from Radix UI, installed one component at a time and styled with our tokens (no shadcn theme). Icons are Lucide.
- Fonts are self-hosted with `next/font/local`, using the files from `Docs/design/05-assets/fonts/`.

**Testing and CI**

- `web-ci` runs eslint (eslint-config-next), `prettier --check` (with the Tailwind plugin), `tsc`, `next build`, Vitest (with Testing Library) and Playwright against `next build` + `next start` (axe for accessibility), then builds the Docker image.

**Hosting**

- `web/Dockerfile` builds `output: "standalone"` and runs `node server.js`. Static export is not possible because of the auth proxy.
- Local: a `web` service in `docker-compose.yml` on port 3000, calling the API inside Docker at `http://api:8000`.
- Staging: a `web` container on the same Compose stack, behind Caddy on its own hostname (`STAGING_WEB_DOMAIN`). The API keeps `STAGING_DOMAIN` for mobile, webhooks and `/docs`. Two hostnames are needed because the web app's `/api/v1/*` is the proxy, while mobile and the payment providers call FastAPI's `/api/v1/*` directly.

## Consequences

- Tokens never reach page JavaScript, so an XSS bug cannot steal a session. The trade-off is one more container and one more hop per request.
- The web app's server owns the refresh rotation. A bug there signs users out (refresh reuse revokes sessions), so the single-flight refresh has its own tests.
- Scaling the web app beyond one instance needs a shared refresh lock first (see above).
- The OpenAPI drift check runs on every backend change, so a backend PR that changes the contract must regenerate the web client in the same PR.

## Amendment (2026-10-22, stage W1a): details found while building the auth proxy

- **Writes check `Origin` (CSRF).** SameSite=Lax cookies alone still allow some cross-site requests, so the API proxy and the `/api/session/*` routes refuse any non-GET request whose `Origin` isn't this site.
- **Three cookies.**
  - `ibh_at` holds the access token (path `/`).
  - `ibh_rt` holds the refresh token on path `/api` only, so it never travels with a page request.
  - `ibh_s` is a plain "a session exists" flag. `src/proxy.ts` uses it to tell a signed-out visitor from an expired token.
- **Pages refresh by redirect.** Server components can't set cookies, and Next runs `src/proxy.ts` apart from the server's own memory, so neither may call the refresh. When a page's access token is about to expire, `src/proxy.ts` redirects to `/api/session/refresh?next=…`. That route handler refreshes through the single-flight module, sets the new cookies and redirects back. The API proxy refreshes inside its own handler.
- **The single-flight result is kept for 30 seconds**, keyed by the old refresh token. A request that was already in flight with the old cookie gets the new pair instead of reusing the old token, which the backend would treat as theft. A failed refresh is kept for the same window and never retried.
- **Sign-out only clears the cookies.** The backend has no sign-out endpoint (MX-19), so the refresh token stays valid on the server until it expires.
