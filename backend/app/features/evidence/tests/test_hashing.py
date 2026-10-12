"""Tests for hashing.py (owner: James). Images are drawn in code so no binary fixtures are needed."""

import asyncio
import io
import sys
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.features.evidence.hashing import (
    REUSE_MAX_DISTANCE,
    ReuseMatch,
    check_reuse,
    compute_phash,
    hamming,
    video_phashes,
)


def site_photo(variant: int = 0, size: tuple[int, int] = (640, 480)) -> Image.Image:
    """A smooth 'photo': a gradient sky, ground and a few blocks, laid out per variant."""
    width, height = size
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        shade = int(80 + 150 * y / height)
        draw.line([(0, y), (width, y)], fill=(shade, shade, 255 - shade // 2))
    if variant == 0:
        draw.rectangle([60, 260, 300, 470], fill=(150, 75, 40))
        draw.rectangle([360, 180, 600, 470], fill=(200, 200, 190))
        draw.ellipse([480, 30, 580, 130], fill=(255, 230, 90))
    else:
        draw.rectangle([20, 20, 300, 200], fill=(30, 30, 30))
        draw.ellipse([250, 200, 620, 470], fill=(20, 160, 60))
        draw.rectangle([40, 300, 200, 460], fill=(240, 240, 240))
    return image


def to_jpeg(image: Image.Image, quality: int = 90) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def crop_border(image: Image.Image, fraction: float) -> Image.Image:
    width, height = image.size
    dx, dy = int(width * fraction), int(height * fraction)
    return image.crop((dx, dy, width - dx, height - dy))


ORIGINAL = compute_phash(to_jpeg(site_photo()))


def test_same_photo_gives_same_hash() -> None:
    assert compute_phash(to_jpeg(site_photo())) == ORIGINAL


def test_resized_photo_matches() -> None:
    resized = site_photo().resize((320, 240))
    assert hamming(ORIGINAL, compute_phash(to_jpeg(resized))) <= REUSE_MAX_DISTANCE


def test_recompressed_photo_matches() -> None:
    assert hamming(ORIGINAL, compute_phash(to_jpeg(site_photo(), quality=40))) <= REUSE_MAX_DISTANCE


def test_cropped_photo_matches() -> None:
    cropped = crop_border(site_photo(), 0.05)
    assert hamming(ORIGINAL, compute_phash(to_jpeg(cropped))) <= REUSE_MAX_DISTANCE


def test_different_photo_does_not_match() -> None:
    assert hamming(ORIGINAL, compute_phash(to_jpeg(site_photo(variant=1)))) > REUSE_MAX_DISTANCE


def test_hash_fits_postgres_bigint() -> None:
    for variant in (0, 1):
        phash = compute_phash(to_jpeg(site_photo(variant)))
        assert -(2**63) <= phash < 2**63


def test_hamming_counts_differing_bits() -> None:
    assert hamming(0, 0) == 0
    assert hamming(0b1011, 0b0001) == 2
    assert hamming(-1, 0) == 64  # all 64 bits set in the signed form
    assert hamming(-1, 2**64 - 1) == 0  # signed and unsigned forms of the same hash


def write_video(path: Path, seconds: int, fps: int = 10) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"MJPG"), fps, (640, 480))
    frame = cv2.cvtColor(np.asarray(site_photo()), cv2.COLOR_RGB2BGR)
    for _ in range(seconds * fps):
        writer.write(frame)
    writer.release()


def test_video_gives_one_hash_per_two_seconds(tmp_path: Path) -> None:
    video = tmp_path / "site.avi"
    write_video(video, seconds=6)
    hashes = video_phashes(video)
    assert len(hashes) == 3  # keyframes at 0 s, 2 s and 4 s
    assert all(hamming(h, ORIGINAL) <= REUSE_MAX_DISTANCE for h in hashes)


def test_unreadable_video_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        video_phashes(tmp_path / "missing.mp4")


# check_reuse() runs SQL, so these tests need Postgres (docker compose up db; CI has one).
# A temporary `evidence` table shadows the real one, so they work before and after it exists.


@pytest.fixture(scope="module")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    # Async psycopg can't run on Windows' default Proactor loop; Linux (CI, Docker) is unaffected.
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.execute(
                text("CREATE TEMP TABLE evidence (id uuid PRIMARY KEY, phash bigint) ON COMMIT DROP")
            )
            yield AsyncSession(bind=connection)
            await connection.rollback()
    except OperationalError:
        pytest.skip("Postgres is not running")
    finally:
        await engine.dispose()


async def store(session: AsyncSession, phash: int | None) -> uuid.UUID:
    evidence_id = uuid.uuid4()
    await session.execute(
        text("INSERT INTO evidence (id, phash) VALUES (:id, :phash)"), {"id": evidence_id, "phash": phash}
    )
    return evidence_id


async def test_check_reuse_finds_a_resized_copy(session: AsyncSession) -> None:
    stored = await store(session, ORIGINAL)
    await store(session, compute_phash(to_jpeg(site_photo(variant=1))))

    match = await check_reuse(session, compute_phash(to_jpeg(site_photo().resize((320, 240)))))

    assert match is not None
    assert match.evidence_id == stored
    assert match.distance <= REUSE_MAX_DISTANCE


async def test_check_reuse_ignores_different_photos(session: AsyncSession) -> None:
    await store(session, compute_phash(to_jpeg(site_photo(variant=1))))
    await store(session, None)

    assert await check_reuse(session, ORIGINAL) is None


async def test_check_reuse_skips_the_evidence_being_checked(session: AsyncSession) -> None:
    itself = await store(session, ORIGINAL)

    assert await check_reuse(session, ORIGINAL, exclude_evidence_id=itself) is None
    assert await check_reuse(session, ORIGINAL) is not None


async def test_check_reuse_handles_negative_hashes(session: AsyncSession) -> None:
    stored = await store(session, -(2**63) + 0b111)

    match = await check_reuse(session, -(2**63) + 0b100)

    assert match == ReuseMatch(evidence_id=stored, distance=2)
