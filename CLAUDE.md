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

## Current state (updated 2026-10-13)
- Phase: **backend only**. Web and Flutter start after the backend gate in the team task doc (`iBackHome_Backend_Tasks.md`, kept outside the repo; ask me for it). Per-person folder ownership is in `.github/CODEOWNERS`; never edit another owner's folder.
- Repo root has `backend/`, `web/` and `mobile/` (READMEs only), `Docs/`, `docker-compose.yml`, `.github/`, `.env.example`, `README.md`.
- **`main` = `2f4e691`**, CI green (530 tests, run 38365058379). Merged: #2–#6 Christopher's Day 1 foundation and fixes; #8 Abigail Day 1 (geo, evidence storage); #1 and #9 James Day 1 (image hashing, Gemini LLM client); #10 Lilian Day 1 (milestones, price index); #12 Christopher Day 2 (login and roles); #14 optional `Idempotency-Key` header. Merged branches are kept; do not delete them (one approved exception: the duplicate `Abigail` branch).
- **Verified:** Fresh clone + `docker compose up` → `/healthz` 200 in ~30 s. CODEOWNERS has 0 errors on GitHub.
- **Day 1 foundation (Christopher, signed off 2026-10-12):**
  - `core/`: settings, async DB session (5 s connect timeout), `TimestampedBase` (UUID id, UTC timestamps), `AppError` + one error shape (catch-all 500 included), `Idempotency-Key` helpers (optional header; key clash → 409, tested under real concurrency), `/healthz` checking database, Redis and storage (200 or 503).
  - `main.py` auto-mounts every feature `router.py` under `/api/v1`; `workers/celery_app.py` auto-registers every `tasks.py` (UTC, JSON).
  - Alembic with PostGIS; `docker compose up` runs api, worker, beat, PostGIS, Redis and SeaweedFS (S3 on :9000). Migration chain on `main`: `0001_base` → `create_milestones` → `create_price_index` → `create_users_and_auth` (head).
  - `backend/conftest.py` gives every test `db_session` (real Postgres, rolled back) and `client`. DB tests skip locally without a database but fail in CI.
  - CI (`.github/workflows/backend-ci.yml`): ruff, mypy, migration up/down/up, pytest, Docker image build, all via uv. Runs only when `backend/**` or the workflow file changes.
- **Contracts on `main` that other modules use:** `from app.base.geo import service as geo` → `parse_polygon(geojson)`, `inside_geofence(session, geofence_ewkt, lat, lon, buffer_m=25)`, `distance_to_fence(...)` (geo never reads `sites`; Christopher owes `projects.service.get_geofence(session, site_id)` → EWKT on Day 3). Milestones: `create_for_project(session, project_id, groups, currency)`, `mark_funded/released/disputed/resolved`. `evidence.hashing.check_reuse()`; `agents.llm.LLMClient`.
- **Day 2 login and roles (Christopher): merged in #12.**
  - Tables `users`, `otp_codes`, `refresh_tokens` (migration `create_users_and_auth`, after `create_price_index`).
  - `POST /auth/otp/request` (optional `channel`: `sms` default or `whatsapp` for a phone, `email` for an email), `POST /auth/otp/verify`, `POST /auth/refresh`, `GET /me`.
  - For every module: `from app.base.users import service as users` → `users.CurrentUserDep`, `Depends(users.require_role("ops"))` (wrong role → 403 `forbidden_role`), `users.get_user(session, id)`. Abigail and Lilian can now import `current_user` and `require_role` from `app.base.users.service`.
  - 89 tests in `base/users`, including races on separate connections.
- **Decisions:**
  - Dependencies live in `backend/pyproject.toml`, one uv group per person (`uv add --group <name> ...`), pinned in `uv.lock`; see `Docs/adr/0002-uv-dependencies.md`. `backend/requirements/*.txt` are unused and will be deleted once open branches merge.
  - Local object storage is SeaweedFS because MinIO no longer publishes images. Staging and production use an S3-compatible service (R2 or B2).
  - The db healthcheck uses TCP (`pg_isready -h 127.0.0.1`): the socket check passed during first-boot PostGIS init and the api's migration failed.
  - Models use plain SQLAlchemy 2 `DeclarativeBase`, not SQLModel (ADR 0001).
  - Login: phone numbers from any country, stored as E.164 (no leading + means Nigerian, `0803...` → `+234803...`), or email. New people sign up as `client`; other roles come from invites, vetting or seeding. User status is `active` or `suspended`. Refresh tokens rotate once (one conditional UPDATE). Reusing a refresh token revokes all of that user's tokens, so mobile must not blindly retry `/auth/refresh` (a retry after a lost response logs the user out). OTP codes and refresh tokens are stored only as hashes; verify/refresh never store responses for `Idempotency-Key`. The development OTP sender logs codes only when `ENVIRONMENT=local`; outside local the app refuses a placeholder `JWT_SECRET`.
  - `Idempotency-Key` is optional by default (fixed in #14): routes write `key: IdempotencyKeyDep` and must NOT add `= None`. `IdempotencyKeyDep` is a small dependency because FastAPI forbids a default inside `Annotated[..., Header(...)]`.
  - GitHub usernames: costechHQ (Christopher), Abigail56 (Abigail), Lilianezeh (Lilian), JaOnwude (James), gabrielnjoku (Gabriel).
- **Open follow-ups:**
  - Each teammate still has to confirm `docker compose up` works on their machine.
  - Migrations: Abigail's `create_devices` and Gabriel's `create_ledger_entries` (PR #11) must now chain after `create_users_and_auth`: rebase onto `main` and change `down_revision`, not after `create_price_index`. `james/day-02-vetting` still chains from `0001_base` and needs the same.
  - Gabriel PR #11 (ledger, escrow): CI fails until his migration chains after `create_users_and_auth`; payments/escrow need two reviewers.
  - Abigail PR #13 (`abigail/day-02-devices-signatures`): CI fails ("Multiple head revisions") until she rebases and chains `create_devices` after `create_users_and_auth`; she can now swap her `auth.py` stand-in for `users.current_user` / `require_role`, add the `devices.user_id` FK to `users`, and drop `= None` from her two `IdempotencyKeyDep` parameters.
  - Lilian: `audit.record()` (Day 2) not on `main` yet; her check-constraint names are doubled (`ck_milestones_ck_...`), cosmetic.
  - Staging proxy: PR #15 open (explicit `--proxy-headers`, `FORWARDED_ALLOW_IPS` documented); set `FORWARDED_ALLOW_IPS` to the proxy's range on staging, or every caller shares one per-IP OTP limit.
  - Spec decision 5: choose an SMS provider that also reaches foreign numbers (Day 5, with Lilian's `notify()`).
  - Docs: spec lists `price_index_entries` under suppliers; the code is Lilian's `features/price_index/`. `LLM_API_KEY` / `LLM_MODEL` in `.env.example`: in PR #15.
  - `main` has no branch protection (Christopher's decision pending).
  - On Christopher's PC: `pikva-postgres` (another project) holds port 5432, so stop it before `docker compose up`; `localhost` (IPv6) doesn't reach Docker ports from the terminal, use `127.0.0.1`; uvicorn run directly on Windows can't use async psycopg (Proactor loop), so run the API in Docker.
- **Not started (Christopher), wait for his go-ahead:** Day 3 projects, sites and membership, Day 4 BoQ, approvals and logging, Day 5 end-to-end test.
- Before starting any task, inspect the code and git branches (`git fetch`, then `git log`) and tell me what already exists. Do not rebuild it.

## Stack
- Backend: Python 3.12, FastAPI, SQLModel/SQLAlchemy 2 (async), Alembic, PostgreSQL 16 + PostGIS, Celery + Redis
- Web: React + TypeScript (Vite). Mobile: Flutter (Android 8+, offline-first)
- Payments: Stripe (in), Paystack (NGN payouts), licensed escrow partner behind the `EscrowProvider` interface (SimulatedEscrow until a partner signs)
- AI: LLM API with tool calling; tools are our own REST endpoints

## Tooling rules (hard)
- JS/TS: `bun` only. Never `npm`, `npx` or `yarn`.
- Python: `uv` only (`uv add`, `uv sync`, `uv run`), run from `backend/`. Never `pip`.
- `backend/requirements*.txt` exist. Do not edit them by hand; tell me if they need regenerating.
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
