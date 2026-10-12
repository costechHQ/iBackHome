# iBackHome

*Far from home, never out of sight.*

iBackHome lets Nigerians abroad build homes in Enugu with confidence: vetted supervisors capture evidence that can't be faked, and money is released milestone by milestone through a licensed escrow partner only when the work is confirmed.

HackathonAfrica 3.0 · Team 4

## Repository layout

```
ibackhome/
├── backend/                FastAPI API, Celery workers, Alembic migrations
│   ├── app/
│   │   ├── core/           config, database, errors, idempotency, auto-discovery
│   │   ├── base/           base modules every feature uses (users, audit, payments, notifications, geo)
│   │   ├── features/       one folder per product feature, one owner each
│   │   ├── workers/        Celery app
│   │   └── main.py         auto-loads every router
│   ├── alembic/            migrations
│   ├── pyproject.toml      dependencies (one uv group per person); uv.lock pins them
│   └── tests/
├── web/                    React app (web phase)
├── mobile/                 Flutter app (Flutter phase)
├── Docs/                   spec.md, PRD, architecture decision records
└── docker-compose.yml
```

Who owns which folder: see `.github/CODEOWNERS`. Only the owner edits a folder; everyone else calls its `service.py`.

## Run it locally (about 10 minutes)

You need Docker Desktop (or Docker Engine with Compose v2.24+), Git, and [uv](https://docs.astral.sh/uv/) for running tests outside Docker.

```bash
git clone <repo-url> ibackhome
cd ibackhome
cp .env.example .env
docker compose up --build
```

Then open:

- API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/healthz> → `{"status": "ok", ...}`
- Object storage (S3 API, SeaweedFS): <http://localhost:9000>, keys `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` from `.env`. It answers about 15 seconds after starting; `docker compose ps` shows it as healthy.

The API container runs `alembic upgrade head` on start, so the database is always migrated.

## Everyday commands

We use **uv** for Python, never pip (see `Docs/adr/0002-uv-dependencies.md`). Run these from the `backend/` folder. `uv sync` creates `.venv` with Python 3.12 and every group; `uv run` keeps it in sync automatically.

| Task | Command |
| --- | --- |
| Install everything | `uv sync` |
| Run tests (needs `docker compose up -d db`) | `uv run pytest -q` |
| Lint and format | `uv run ruff check . && uv run ruff format .` |
| Type check | `uv run mypy app` |
| Add a package to your group | `uv add --group <your-name> <package>` |
| New migration for your tables | `uv run alembic revision --autogenerate -m "add milestones"` |
| Apply migrations | `uv run alembic upgrade head` |
| Two migration heads after a merge | `uv run alembic merge heads -m "merge"` (Christopher, at the 17:00 merge) |
| `uv.lock` conflict after a merge | Take either side, then `uv lock` (never edit it by hand) |

Inside the API container (`docker compose exec api sh`) the tools are on the path directly: `pytest -q`, `alembic upgrade head`.

Tests share fixtures from `backend/conftest.py`: `db_session` (real Postgres, rolled back after each test) and `client` (HTTP calls into the app using that session). Without a database, DB tests are skipped locally but fail in CI.

## How to add your feature

1. Work only in your own folder, e.g. `backend/app/features/milestones/`.
2. Tables go in `models.py` (inherit `TimestampedBase`), shapes in `schemas.py`, rules in `service.py`, endpoints in `router.py` (the `router` object is mounted under `/api/v1` automatically), background jobs in `tasks.py`.
3. Raise `AppError("code", "message", status)` for errors so every response has the same shape.
4. Need a package? `uv add --group <your-name> <package>` from `backend/`, and commit `pyproject.toml` and `uv.lock` together. (`backend/requirements/*.txt` are no longer used and will be removed once the open branches merge.)
5. Need something from another feature? Ask its owner to expose a function in their `service.py`.
6. Write tests in your folder's `tests/`. Anything that moves money needs tests before it's merged.

## Daily rhythm

- 09:00 stand-up (chair rotates daily)
- One branch per person per day: `<name>/day-<n>-<topic>`
- Open your pull request by 16:30; merge and deploy to staging at 17:00
- CI (lint, types, migrations, tests) must be green before merging

## Docs

- `Docs/spec.md` — technical specification (data model, ERD, state machines, API, evidence integrity, payments)
- `Docs/adr/` — architecture decision records
- PRD, task breakdowns and the non-coding plan live in the team's shared docs
