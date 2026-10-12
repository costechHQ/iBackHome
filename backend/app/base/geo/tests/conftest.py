import asyncio
import sys
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings

# A ~100 m x 100 m site in Enugu. Latitude 6.4600 is its north edge.
SITE_SW = (7.5000, 6.4590)  # (lon, lat)
SITE_NE = (7.5009, 6.4600)
M_PER_DEG_LAT = 111_195.0

if sys.platform == "win32":  # psycopg async cannot use the default Proactor loop
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            # Temp table shadows the real `sites` table for this connection only.
            await conn.execute(
                text("CREATE TEMP TABLE sites (id uuid PRIMARY KEY, geofence geometry(Polygon, 4326))")
            )
            yield AsyncSession(bind=conn, expire_on_commit=False)
    except OperationalError:
        pytest.skip("PostGIS database not reachable")
    finally:
        await engine.dispose()


@pytest.fixture
async def site_id(session: AsyncSession) -> uuid.UUID:
    sid = uuid.uuid4()
    (w, s), (e, n) = SITE_SW, SITE_NE
    await session.execute(
        text("INSERT INTO sites VALUES (:id, ST_GeomFromEWKT(:g))"),
        {"id": sid, "g": f"SRID=4326;POLYGON(({w} {s}, {e} {s}, {e} {n}, {w} {n}, {w} {s}))"},
    )
    return sid
