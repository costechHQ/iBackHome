"""The ledger migration upgrades from an empty database, downgrades one step and upgrades again.

Runs Alembic in a subprocess against a scratch database so the shared test database is untouched.
"""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

BACKEND = Path(__file__).parents[4]
DOWN_REVISION = "create_spot_checks"

# alembic's CLI, but on Windows with the selector loop async psycopg needs (no-op on Linux / CI).
RUN_ALEMBIC = (
    "import asyncio, sys\n"
    "if sys.platform == 'win32':\n"
    "    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())\n"
    "from alembic.config import main\n"
    "main(argv=sys.argv[1:])\n"
)


def _alembic(url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-c", RUN_ALEMBIC, *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


async def _ledger_objects(url: str) -> dict[str, bool]:
    eng = create_async_engine(url, poolclass=NullPool)
    try:
        async with eng.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT to_regclass('ledger_entries') IS NOT NULL, "
                        "EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'ledger_entries_balanced'), "
                        "EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'ledger_entries_check_balanced')"
                    )
                )
            ).one()
    finally:
        await eng.dispose()
    return {"table": row[0], "trigger": row[1], "function": row[2]}


async def test_upgrade_from_empty_and_downgrade_one_step(engine: AsyncEngine) -> None:
    scratch = f"ibackhome_migtest_{uuid.uuid4().hex[:8]}"
    base_url = make_url(str(engine.url.render_as_string(hide_password=False)))
    scratch_url = base_url.set(database=scratch).render_as_string(hide_password=False)

    admin = create_async_engine(base_url, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            try:
                await conn.execute(text(f'CREATE DATABASE "{scratch}"'))
            except Exception as exc:  # pragma: no cover - only without CREATEDB
                pytest.skip(f"cannot create a scratch database: {exc.__class__.__name__}")
        try:
            _alembic(scratch_url, "upgrade", "head")
            assert await _ledger_objects(scratch_url) == {"table": True, "trigger": True, "function": True}

            _alembic(scratch_url, "downgrade", DOWN_REVISION)
            assert await _ledger_objects(scratch_url) == {"table": False, "trigger": False, "function": False}

            _alembic(scratch_url, "upgrade", "head")
            assert (await _ledger_objects(scratch_url))["table"]
        finally:
            async with admin.connect() as conn:
                await conn.execute(text(f'DROP DATABASE IF EXISTS "{scratch}" WITH (FORCE)'))
    finally:
        await admin.dispose()
