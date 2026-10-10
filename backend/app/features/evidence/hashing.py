"""Perceptual image fingerprints for spotting reused photos and videos.

Owner: James. Abigail's evidence checks call `check_reuse()` as the last check.

A pHash is 64 bits. Postgres has no unsigned 64-bit integer, so every hash we hand out is
the signed `bigint` form (two's complement) that goes straight into `evidence.phash`.
Two images are "the same" when their hashes differ in at most `REUSE_MAX_DISTANCE` bits.

    phash = compute_phash(image_bytes)
    match = await check_reuse(session, phash, exclude_evidence_id=evidence.id)
    if match:
        ...  # flag the evidence, citing match.evidence_id
"""

import io
import uuid
from dataclasses import dataclass
from pathlib import Path

import cv2
import imagehash
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

REUSE_MAX_DISTANCE = 8
VIDEO_KEYFRAME_SECONDS = 2.0

_BITS = 64
_MASK = (1 << _BITS) - 1


@dataclass(frozen=True)
class ReuseMatch:
    evidence_id: uuid.UUID
    distance: int


def _to_signed(value: int) -> int:
    """Unsigned 64-bit hash -> signed bigint, so it fits a Postgres bigint column."""
    return value - (1 << _BITS) if value >= 1 << (_BITS - 1) else value


def _hash_image(image: Image.Image) -> int:
    return _to_signed(int(str(imagehash.phash(image)), 16))


def compute_phash(image_bytes: bytes) -> int:
    """64-bit perceptual hash of a photo, as a signed bigint."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        return _hash_image(image)


def video_phashes(path: str | Path) -> list[int]:
    """One pHash per keyframe, taken every 2 seconds from the start of the video."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"cannot read video: {path}")
    try:
        hashes: list[int] = []
        position_ms = 0.0
        while True:
            capture.set(cv2.CAP_PROP_POS_MSEC, position_ms)
            ok, frame = capture.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hashes.append(_hash_image(Image.fromarray(rgb)))
            position_ms += VIDEO_KEYFRAME_SECONDS * 1000
        return hashes
    finally:
        capture.release()


def hamming(a: int, b: int) -> int:
    """Number of differing bits between two hashes (signed or unsigned form)."""
    return ((a ^ b) & _MASK).bit_count()


# `#` is XOR on bigint; casting to bit(64) keeps the two's complement bits for bit_count().
_NEAREST_MATCH = text(
    """
    SELECT id, bit_count((phash # :phash)::bit(64)) AS distance
    FROM evidence
    WHERE phash IS NOT NULL
      AND (CAST(:exclude_id AS uuid) IS NULL OR id <> CAST(:exclude_id AS uuid))
      AND bit_count((phash # :phash)::bit(64)) <= :max_distance
    ORDER BY distance
    LIMIT 1
    """
)


async def check_reuse(
    session: AsyncSession, phash: int, exclude_evidence_id: uuid.UUID | None = None
) -> ReuseMatch | None:
    """Closest stored image (across all projects) within the reuse distance, or None."""
    row = (
        await session.execute(
            _NEAREST_MATCH,
            {"phash": phash, "exclude_id": exclude_evidence_id, "max_distance": REUSE_MAX_DISTANCE},
        )
    ).first()
    return ReuseMatch(evidence_id=row.id, distance=row.distance) if row else None
