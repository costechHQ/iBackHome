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

## Current state
- Repo root has `backend/`, `web/`, `mobile/`, `Docs/`, `docker-compose.yml`, `.github/`, `.env.example`, `README.md`.
- Backend scaffold exists in `backend/app/` (`core/`, `base/`, `features/`, `workers/`, `main.py`) with Alembic, tests, Dockerfile.
- Done so far: core settings, database connection, error handling, health check, idempotency support.
- Before starting any task, inspect the code and tell me what already exists. Do not rebuild it.

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
