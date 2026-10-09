# ADR 0001: Feature-based folders with one owner each

- **Status:** Accepted
- **Date:** Programme day 4
- **Owner:** Christopher

## Context

Five people build the backend at the same time over five days. A layered structure (all models in one folder, all routes in another) would put everyone in the same files every day and cause merge conflicts.

## Decision

- One folder per feature under `backend/app/features/`, and one per base module under `backend/app/base/`. Each folder has exactly one owner (see `.github/CODEOWNERS`).
- Inside each folder, the same files: `router.py`, `schemas.py`, `models.py`, `service.py`, `tasks.py` (if needed), `tests/`.
- `main.py`, the Celery app and Alembic find every `router.py`, `tasks.py` and `models.py` automatically (`app/core/discovery.py`), so nobody edits a shared file to add code.
- Features call each other only through the other feature's `service.py`, never by querying its tables.
- Each person adds Python packages only to their own `backend/requirements/<name>.txt`.
- We use SQLAlchemy 2 (async) with `DeclarativeBase` directly rather than SQLModel, so models, migrations and type checking all use one well-documented API.

## Consequences

- Merges rarely conflict; when two Alembic migrations both follow the same parent, Christopher runs `alembic merge heads` at the 17:00 merge.
- A feature can be cut by removing its folder.
- Cross-feature calls must be agreed at stand-up (see "Functions each person provides" in the Backend Tasks doc).
