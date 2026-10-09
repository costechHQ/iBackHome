# iBackHome

*Far from home, never out of sight.*

iBackHome lets Nigerians abroad build homes in Enugu with confidence: vetted supervisors capture evidence that can't be faked, and money is released milestone by milestone through a licensed escrow partner only when the work is confirmed.

HackathonAfrica 3.0 · Team 4

## Repository layout

ibackhome/
├── backend/                FastAPI API, Celery workers, Alembic migrations
│   ├── app/
│   │   ├── core/           config, database, errors, idempotency, auto-discovery
│   │   ├── base/           base modules every feature uses (users, audit, payments, notifications, geo)
│   │   ├── features/       one folder per product feature, one owner each
│   │   ├── workers/        Celery app
│   │   └── main.py         auto-loads every router
│   ├── alembic/            migrations
│   ├── requirements/       one requirements file per person
│   └── tests/
├── web/                    React app (web phase)
├── mobile/                 Flutter app (Flutter phase)
├── docs/                   spec.md, architecture decision records
└── docker-compose.yml
```

Who owns which folder: see `.github/CODEOWNERS`. Only the owner edits a folder; everyone else calls its `service.py`.

## Run it locally (about 10 minutes)

You need Docker Desktop (or Docker Engine with Compose v2.24+) and Git.

```bash
git clone <repo-url> ibackhome
cd ibackhome
cp .env.example .env
docker compose up --build
```

Then open:

- API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/healthz> → `{"status": "ok", ...}`
- MinIO console: <http://localhost:9001> (minioadmin / minioadmin)

The API container runs `alembic upgrade head` on start, so the database is always migrated.

## Everyday commands

Run these from the `backend/` folder inside the API container (`docker compose exec api sh`) or in a local virtualenv (`pip install -r requirements-dev.txt`):

| Task | Command |
| --- | --- |
| Run tests | `pytest -q` |
| Lint and format | `ruff check . && ruff format .` |
| Type check | `mypy app` |
| New migration for your tables | `alembic revision --autogenerate -m "add milestones"` |
| Apply migrations | `alembic upgrade head` |
| Two migration heads after a merge | `alembic merge heads -m "merge"` (Christopher, at the 17:00 merge) |

## How to add your feature

1. Work only in your own folder, e.g. `backend/app/features/milestones/`.
2. Tables go in `models.py` (inherit `TimestampedBase`), shapes in `schemas.py`, rules in `service.py`, endpoints in `router.py` (the `router` object is mounted under `/api/v1` automatically), background jobs in `tasks.py`.
3. Raise `AppError("code", "message", status)` for errors so every response has the same shape.
4. Need a package? Add it to `backend/requirements/<your-name>.txt`.
5. Need something from another feature? Ask its owner to expose a function in their `service.py`.
6. Write tests in your folder's `tests/`. Anything that moves money needs tests before it's merged.

## Daily rhythm

- 09:00 stand-up (chair rotates daily)
- One branch per person per day: `<name>/day-<n>-<topic>`
- Open your pull request by 16:30; merge and deploy to staging at 17:00
- CI (lint, types, migrations, tests) must be green before merging

## Docs

- `docs/spec.md` — technical specification (data model, ERD, state machines, API, evidence integrity, payments)
- `docs/adr/` — architecture decision records
- PRD, task breakdowns and the non-coding plan live in the team's shared docs
