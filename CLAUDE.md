# iBackHome

Far from home, never out of sight. Nigerians abroad build homes in Enugu: verified supervisors capture
tamper-proof site evidence, and money is released milestone by milestone through a licensed escrow partner
only after supervisor verification and client approval. We are not a construction company and we never hold client funds.

## Source of truth
- `Docs/spec.md` is the Technical Specification (how). Treat it as authoritative.
- The PRD (what and why, requirement IDs FR-xx) is the file in `Docs/` whose name starts with "iBackHome — Product Requirements Document".
- Ignore the other copy in `Docs/` named "...Technical Specification with ERD.md". It duplicates `spec.md`.
- Architecture decisions live in `Docs/adr/`. Read them before changing structure.
- If code and spec disagree, stop and ask me. Do not silently pick one.

## Current state (updated 2026-10-14)
- Phase: **backend only**. Web and Flutter start after the backend gate in the team task doc (`iBackHome_Backend_Tasks.md`, kept outside the repo; ask me for it). Per-person folder ownership is in `.github/CODEOWNERS`; never edit another owner's folder.
- Repo root has `backend/`, `web/` and `mobile/` (READMEs only), `Docs/`, `docker-compose.yml`, `.github/`, `.env.example`, `README.md`.
- **`main` = `555f692`**, CI green (965 tests, run 38530206489). No open PRs. Merged branches are kept; do not delete them (one approved exception: the duplicate `Abigail` branch).
  - Day 1: #2–#6 Christopher foundation and fixes; #7, #8 Abigail (geo, evidence storage); #1, #9 James (image hashing, Gemini LLM client); #10 Lilian (milestones, price index); #11, #19 Gabriel (ledger, escrow interface).
  - Day 2: #12 Christopher (login and roles); #13 Abigail (devices, signatures); #17 Lilian (audit log, milestone claim); #18 James (supervisor vetting, spot checks, `scripts/seed.py`); #20 Gabriel (`escrow.request_release` stub).
  - Other: #14 optional `Idempotency-Key`; #15 proxy headers and LLM env vars; #16 docs.
  - Day 3: #21 Christopher (projects, sites and membership).
- **Verified:** Fresh clone + `docker compose up` → `/healthz` 200 in ~30 s (checked after Day 1). CODEOWNERS has 0 errors on GitHub.
- **Migration chain on `main`:** `0001_base` → `create_milestones` → `create_price_index` → `create_users_and_auth` → `create_devices` → `create_supervisor_profiles` → `create_spot_checks` → `create_ledger_entries` → `create_audit_log` → `create_projects_and_sites` (head). A new migration chains after the head on `main` at the time it merges; two heads fail CI with "Multiple head revisions".
- **Day 1 foundation (Christopher, signed off 2026-10-12):**
  - `core/`: settings, async DB session (5 s connect timeout), `TimestampedBase` (UUID id, UTC timestamps), `AppError` + one error shape (catch-all 500 included), `Idempotency-Key` helpers (optional header; key clash → 409, tested under real concurrency), `/healthz` checking database, Redis and storage (200 or 503), `pagination.py` (cursor helpers for `?cursor=&limit=`, added Day 3).
  - `main.py` auto-mounts every feature `router.py` under `/api/v1`; `workers/celery_app.py` auto-registers every `tasks.py` (UTC, JSON).
  - Alembic with PostGIS; `docker compose up` runs api, worker, beat, PostGIS, Redis and SeaweedFS (S3 on :9000).
  - `backend/conftest.py` gives every test `db_session` (real Postgres, rolled back) and `client`. DB tests skip locally without a database but fail in CI.
  - CI (`.github/workflows/backend-ci.yml`): ruff, mypy, migration up/down/up, pytest, Docker image build, all via uv. Runs only when `backend/**` or the workflow file changes.
- **Day 2 login and roles (Christopher, #12):** tables `users`, `otp_codes`, `refresh_tokens`; `POST /auth/otp/request` (optional `channel`: `sms` default or `whatsapp` for a phone, `email` for an email), `POST /auth/otp/verify`, `POST /auth/refresh`, `GET /me`.
- **Day 3 projects, sites and membership (Christopher, #21):**
  - Tables `projects` (status, currency, `budget_minor` > 0; `contractor_id` and `supervisor_id` nullable) and `sites` (one per project; pin POINT + geofence POLYGON, SRID 4326, GiST on `geofence`).
  - `POST /projects` (client; optional `contractor_phone` invites the contractor), `GET /projects` (own projects, ops all, paginated), `GET /projects/{id}` (with site), `PUT /projects/{id}/site` (the project's client or ops; pin must be inside the fence, else 422 `pin_outside_geofence`).
  - Project status machine in `features/projects/transitions.py`, also in `Docs/spec.md`: draft→boq_review (contractor), boq_review→draft (client, contractor, ops), boq_review→active (system), active⇄paused (ops), active→completed (system). Day 3 only creates `draft`.
- **Contracts on `main` that other modules use** (call only through each module's `service.py`):
  - Users: `from app.base.users import service as users` → `users.CurrentUserDep`, `Depends(users.require_role("ops"))` (wrong role → 403 `forbidden_role`), `users.get_user(session, id)`, `users.invite_contractor(session, phone)`.
  - Projects: `from app.features.projects import service as projects` → `require_project_member(session, user, project_id)` (403 `not_project_member`; client, contractor, assigned supervisor or ops), `get_project(session, project_id)`, `get_project_geofence(session, project_id)` / `get_geofence(session, site_id)` → EWKT, `set_supervisor(session, project_id, supervisor_id, actor_id)` (runs `supervision.ensure_assignable()` itself), `get_contractor_phone(...)`, `transition(session, project_id, to_status, actor_role, actor_id)`.
  - Geo: `parse_polygon(geojson)`, `inside_geofence(session, geofence_ewkt, lat, lon, buffer_m=25)`, `distance_to_fence(...)` (geo never reads `sites`).
  - Audit: `from app.base import audit` → `audit.record(session, actor_id, action, object_type, object_id, before, after, request)`, `audit.snapshot(obj)`; `GET /ops/audit`.
  - Milestones: `create_for_project(session, project_id, groups, currency)`, `mark_funded/released/disputed/resolved`, `POST /milestones/{id}/claim`.
  - Supervision: `is_vetted()`, `ensure_assignable()`, spot-check functions. Evidence: `register_device()`, `signing.verify_signature()`, `hashing.check_reuse()`. Payments: `post_transaction()`, `balance()`. Escrow: `request_release()` (stub), `EscrowProvider` / `SimulatedEscrow`. Agents: `llm.LLMClient`.
- **Decisions:**
  - Dependencies live in `backend/pyproject.toml`, one uv group per person (`uv add --group <name> ...`), pinned in `uv.lock`; see `Docs/adr/0002-uv-dependencies.md`. The old `backend/requirements*.txt` files were deleted on 2026-10-14; never use `pip` or requirements files.
  - Local object storage is SeaweedFS because MinIO no longer publishes images. Staging and production use an S3-compatible service (R2 or B2).
  - The db healthcheck uses TCP (`pg_isready -h 127.0.0.1`): the socket check passed during first-boot PostGIS init and the api's migration failed.
  - Models use plain SQLAlchemy 2 `DeclarativeBase`, not SQLModel (ADR 0001). Geometry columns use `geoalchemy2`.
  - Login: phone numbers from any country, stored as E.164 (no leading + means Nigerian, `0803...` → `+234803...`), or email. New people sign up as `client`; other roles come from invites, vetting or seeding. User status is `active` or `suspended`. Refresh tokens rotate once (one conditional UPDATE). Reusing a refresh token revokes all of that user's tokens, so mobile must not blindly retry `/auth/refresh` (a retry after a lost response logs the user out). OTP codes and refresh tokens are stored only as hashes; verify/refresh never store responses for `Idempotency-Key`. The development OTP sender logs codes only when `ENVIRONMENT=local`; outside local the app refuses a placeholder `JWT_SECRET`.
  - `Idempotency-Key` is optional by default (fixed in #14): routes write `key: IdempotencyKeyDep` and must NOT add `= None`. `IdempotencyKeyDep` is a small dependency because FastAPI forbids a default inside `Annotated[..., Header(...)]`.
  - Projects (agreed 2026-10-14): a contractor invite for a new number creates an active contractor (their first OTP login lands on it); a number of another role → 409 `role_conflict`, role unchanged. A contractor is optional at creation, required before the BoQ. Suspended accounts can't be invited or assigned; a completed project can't get a new supervisor.
  - Site lock (decided 2026-10-14): a client can set or change the site only while the project is `draft` or `boq_review` (else 409 `site_locked`); ops can change it at any time; every change is audited.
  - GitHub usernames: costechHQ (Christopher), Abigail56 (Abigail), Lilianezeh (Lilian), JaOnwude (James), gabrielnjoku (Gabriel).
- **Open follow-ups:**
  - James: wire `POST /projects/{id}/supervisor` (his route) and `POST /projects/{id}/spot-checks` to `projects.service`; add FK `spot_checks.project_id → projects`.
  - Lilian: replace `milestones/project_check.py` (returns 503 `projects_not_ready` until then, so claims fail) with `projects.get_project()`; add FK `milestones.project_id → projects`. Doubled check-constraint names (`ck_milestones_ck_...`), cosmetic.
  - Abigail: evidence checks call `projects.get_project_geofence()`.
  - Gabriel: doubled check-constraint names in `create_ledger_entries` (use `op.f`), cosmetic.
  - Each teammate still has to confirm `docker compose up` works on their machine.
  - Staging: set `FORWARDED_ALLOW_IPS` to the proxy's range, or every caller shares one per-IP OTP limit.
  - Spec decision 5: choose an SMS provider that also reaches foreign numbers (Day 5, with Lilian's `notify()`). The invite SMS to a new contractor waits for it.
  - Docs: spec lists `price_index_entries` under suppliers; the code is Lilian's `features/price_index/`. Spec API table lacks `POST /devices/{id}/revoke` and James's supervisor-profile routes.
  - `main` has no branch protection (Christopher's decision pending).
  - On Christopher's PC: `pikva-postgres` (another project) holds port 5432, so stop it before `docker compose up` (tests can use a temporary PostGIS on 5433); `localhost` (IPv6) doesn't reach Docker ports from the terminal, use `127.0.0.1`; uvicorn run directly on Windows can't use async psycopg (Proactor loop), so run the API in Docker.
- **Not started (Christopher), wait for his go-ahead:** Day 4 BoQ, approvals and logging; Day 5 end-to-end test.
- Before starting any task, inspect the code and git branches (`git fetch`, then `git log`) and tell me what already exists. Do not rebuild it.

## Stack
- Backend: Python 3.12, FastAPI, SQLAlchemy 2 (async, plain `DeclarativeBase`; ADR 0001), Alembic, PostgreSQL 16 + PostGIS, Celery + Redis
- Web: React + TypeScript (Vite). Mobile: Flutter (Android 8+, offline-first)
- Payments: Stripe (in), Paystack (NGN payouts), licensed escrow partner behind the `EscrowProvider` interface (SimulatedEscrow until a partner signs)
- AI: LLM API with tool calling; tools are our own REST endpoints

## Tooling rules (hard)
- JS/TS: `bun` only. Never `npm`, `npx` or `yarn`.
- Python: `uv` only (`uv add`, `uv sync`, `uv run`), run from `backend/`. Never `pip`.
- Dependencies: only `backend/pyproject.toml` + `uv.lock` (ADR 0002). There are no requirements files.
- Lint/type: `ruff`, `mypy` (backend); `eslint`, `prettier`, `tsc` (web); `dart analyze` (mobile).
- I use Git Bash on Windows. Give commands that work in Git Bash.

## Architecture rules
1. Features talk to each other only through each other's `service.py`; never query another feature's tables.
2. Code shared by two or more features goes in `core/` or `base/` (backend) or `common/` (web).
3. Only `base/payments` and `features/escrow` move money. Changes there need two reviewers and tests before merge.
4. AI agents call the REST API only, never services or the database. Agent tokens have a tool allow-list; no agent can approve, release, resolve or pay.
5. State changes happen only in the feature's `service.py`, are checked against the allowed transitions in the spec, and write an audit log entry. Invalid transition: HTTP 409.
6. Each feature folder has `router.py`, `schemas.py`, `models.py`, `service.py`, `tasks.py` (if needed), `tests/`.

## Money and data rules (never break)
- Money is integer minor units (`*_minor` BIGINT) plus ISO 4217 `currency`. No floats for money, ever.
- Timestamps stored in UTC.
- `ledger_entries` and `audit_log` are append-only (no UPDATE/DELETE grants); every `transaction_id` must balance.
- Webhooks: verify signature first, insert into `payment_events` (unique provider+event_id), process ledger + state + audit in one transaction. Duplicate event returns 200 and does nothing.
- Every write endpoint accepts `Idempotency-Key`. Errors use `{"error": {"code": "...", "message": "..."}}`. API under `/api/v1`.
- Money figures in any AI output must come from a ledger result, never from the model.

## Evidence integrity (the core promise)
In-app camera only (no gallery, no `image_picker`); device-signed metadata (ECDSA P-256, Android Keystore); server checks in order:
file hash, signature, device owner, clock (10 min drift, 72 h upload window), geofence (25 m buffer), pHash reuse (Hamming <= 8).
The server decides; the device only warns.

## How to work with me
- One meaningful task at a time. Give exact file paths and commands.
- Read the relevant spec section before coding. Start non-trivial work in plan mode.
- Write tests with the code. Anything touching money, state transitions, permissions or evidence checks must have tests.
- Commit at checkpoints with conventional commit messages (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- End every task with four labelled lists: Completed, Tested, Simulated, Pending.
- Never invent endpoints, tables or states that are not in the spec. Propose them first.
- Never put secrets in the repo; `.env.example` lists variables with no real values.
- For run and test commands, read `README.md` and `docker-compose.yml` rather than guessing.
