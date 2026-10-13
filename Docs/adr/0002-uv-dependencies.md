# ADR 0002: uv manages Python dependencies, one group per person

- **Status:** Accepted
- **Date:** 2026-10-12
- **Owner:** Christopher
- **Supersedes:** the "one `backend/requirements/<name>.txt` per person" bullet of ADR 0001

## Context

The scaffold installed packages with `pip install -r requirements-dev.txt` from five per-person files. Nothing was pinned, so two machines (or CI on two days) could install different versions, and the lock file `uv.lock` existed but locked nothing because `pyproject.toml` declared no dependencies. The team agreed to use uv for Python, on Python 3.12.

## Decision

- `backend/pyproject.toml` is the single list of dependencies. Core runtime packages (FastAPI, SQLAlchemy, Celery, ...) are in `[project] dependencies`. Each person's extra packages are in their own dependency group: `christopher`, `abigail`, `lilian`, `james`, `gabriel`, plus `dev` for test and lint tools.
- Add a package with `uv add --group <your-name> <package>`. Commit `pyproject.toml` and `uv.lock` together.
- `[tool.uv] default-groups = "all"`, so `uv sync` and `uv run` always give the full environment.
- Python is pinned to 3.12 (`.python-version`, `requires-python = ">=3.12,<3.13"`).
- Docker and CI install with `uv sync --locked`, which fails if `uv.lock` is out of date with `pyproject.toml`. In the image the virtualenv is `/opt/venv`, because docker compose mounts the source over `/app`.
- `backend/requirements/*.txt` stay in place, unused, until the open branches that edit them have merged, and are then removed in a separate PR.

## Consequences

- Everyone, CI and Docker run exactly the same package versions.
- Two people now edit `pyproject.toml` (in different groups) and `uv.lock`. A conflict in `uv.lock` is resolved by taking either side and running `uv lock`, never by hand-editing.
- A group per person keeps ownership visible, even though the file is shared.
- When James's and others' branches merge, their additions to `requirements/<name>.txt` must be re-added with `uv add --group <name> ...` (for example James's `opencv-python-headless` and `google-genai`).
