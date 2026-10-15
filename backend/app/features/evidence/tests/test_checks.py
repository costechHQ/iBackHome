"""One test per server check, in the order they run, plus the outcomes and safety rules around them."""

import base64
import hashlib
import io
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.base.users.models import User
from app.core.config import get_settings
from app.features.evidence import checks, hashing, service, storage
from app.features.evidence.models import Evidence
from app.features.evidence.schemas import EvidenceIn
from app.features.evidence.signing import canonical_payload
from app.features.evidence.tests.conftest import World, make_user, make_world
from app.features.projects import service as projects
from app.features.projects.schemas import Pin, SiteSet

# About 88 m x 78 m in Independence Layout, Enugu, [lon, lat] as GeoJSON wants.
FENCE = {
    "type": "Polygon",
    "coordinates": [
        [[7.5135, 6.4480], [7.5143, 6.4480], [7.5143, 6.4487], [7.5135, 6.4487], [7.5135, 6.4480]]
    ],
}
INSIDE = (6.4483, 7.5139)  # lat, lon
NORTH_EDGE_LAT = 6.4487
M_PER_DEG_LAT = 111_195.0


def photo(seed: int, size: int = 256) -> bytes:
    """A JPEG of random shapes. Different seeds give clearly different pHashes."""
    rng = random.Random(seed)  # noqa: S311 - test images, not security
    image = Image.new("RGB", (size, size), (rng.randrange(256), rng.randrange(256), rng.randrange(256)))
    draw = ImageDraw.Draw(image)
    for _ in range(14):
        x1, y1 = rng.randrange(size), rng.randrange(size)
        box = (x1, y1, min(size, x1 + rng.randrange(20, 120)), min(size, y1 + rng.randrange(20, 120)))
        colour = (rng.randrange(256), rng.randrange(256), rng.randrange(256))
        (draw.ellipse if rng.random() < 0.5 else draw.rectangle)(box, fill=colour)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=90)
    return out.getvalue()


def resized(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data)).resize((180, 180))
    out = io.BytesIO()
    image.save(out, "JPEG", quality=80)
    return out.getvalue()


@dataclass
class Phone:
    user: User
    device_id: str
    key: ec.EllipticCurvePrivateKey


async def register_phone(session: AsyncSession, user: User, device_id: str | None = None) -> Phone:
    key = ec.generate_private_key(ec.SECP256R1())
    public = base64.b64encode(
        key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    ).decode()
    device_id = device_id or f"phone-{uuid.uuid4()}"
    await service.register_device(session, user.id, device_id, public)
    return Phone(user, device_id, key)


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    w = await make_world(db_session)
    await projects.set_site(
        db_session, w.ops, w.project.id, SiteSet(location=Pin(lat=INSIDE[0], lon=INSIDE[1]), geofence=FENCE)
    )
    return w


@pytest.fixture
async def phone(db_session: AsyncSession, world: World) -> Phone:
    return await register_phone(db_session, world.supervisor)


async def submit(
    session: AsyncSession,
    world: World,
    phone: Phone,
    s3: Any,
    data: bytes | None = None,
    *,
    kind: str = "photo",
    stored: bytes | None = None,
    captured_at: datetime | None = None,
    gps_time: datetime | None = None,
    lat: float = INSIDE[0],
    lon: float = INSIDE[1],
    sign_lat: float | None = None,
    device_id: str | None = None,
    signer: ec.EllipticCurvePrivateKey | None = None,
    user: User | None = None,
) -> Evidence:
    """Upload a file, sign it like the phone does and save it as pending_checks."""
    data = data if data is not None else photo(1)
    captured_at = captured_at or datetime.now(UTC) - timedelta(minutes=1)
    gps_time = gps_time or captured_at - timedelta(seconds=2)
    lat, lon = round(lat, 6), round(lon, 6)
    key = f"evidence/{world.project.id}/{uuid.uuid4()}.{'jpg' if kind == 'photo' else 'mp4'}"
    content_type = "image/jpeg" if kind == "photo" else "video/mp4"
    s3.put_object(
        Bucket=get_settings().storage_bucket,
        Key=key,
        Body=stored if stored is not None else data,
        ContentType=content_type,
    )
    sha = hashlib.sha256(data).hexdigest()
    device_id = device_id or phone.device_id
    payload = canonical_payload(
        sha,
        captured_at,
        gps_time,
        sign_lat if sign_lat is not None else lat,
        lon,
        8.5,
        world.project.id,
        device_id,
    )
    signature = base64.b64encode((signer or phone.key).sign(payload, ec.ECDSA(hashes.SHA256()))).decode()
    body = EvidenceIn(
        project_id=world.project.id,
        milestone_id=world.milestone.id,
        kind=kind,  # type: ignore[arg-type]
        storage_key=key,
        file_sha256=sha,
        captured_at=captured_at,
        gps_time=gps_time,
        latitude=lat,
        longitude=lon,
        accuracy_m=8.5,
        device_id=device_id,
        signature=signature,
    )
    evidence, _ = await service.submit_evidence(session, user or phone.user, body)
    return evidence


async def decide(session: AsyncSession, evidence: Evidence) -> Evidence:
    return await checks.run_checks(session, evidence.id)


# the happy path


async def test_a_good_capture_is_accepted(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await decide(db_session, await submit(db_session, world, phone, s3))
    assert evidence.status == "accepted"
    assert evidence.reject_reason is None
    assert evidence.phash is not None  # stored so later uploads can be compared with it


async def test_the_decision_is_written_to_the_audit_log(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await decide(db_session, await submit(db_session, world, phone, s3))
    entries = list(
        await db_session.scalars(
            select(AuditEntry).where(AuditEntry.object_id == evidence.id).order_by(AuditEntry.at)
        )
    )
    assert [e.action for e in entries] == ["evidence.submitted", "evidence.accepted"]
    assert entries[1].actor_id is None  # decided by the system
    assert entries[1].before is not None and entries[1].before["status"] == "pending_checks"
    assert entries[1].after is not None and entries[1].after["status"] == "accepted"


# 1. file hash


async def test_check_1_file_that_differs_from_the_signed_hash_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await decide(db_session, await submit(db_session, world, phone, s3, photo(1), stored=photo(2)))
    assert evidence.status == "rejected"
    assert "hash" in (evidence.reject_reason or "")


async def test_check_1_missing_file_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await submit(db_session, world, phone, s3)
    storage.delete_object(evidence.storage_key)
    assert (await decide(db_session, evidence)).status == "rejected"


# 2. signature


async def test_check_2_signature_over_different_data_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await decide(db_session, await submit(db_session, world, phone, s3, sign_lat=6.4484))
    assert evidence.status == "rejected"
    assert "signature" in (evidence.reject_reason or "")


async def test_check_2_signature_from_another_key_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    other = ec.generate_private_key(ec.SECP256R1())
    evidence = await decide(db_session, await submit(db_session, world, phone, s3, signer=other))
    assert evidence.status == "rejected"
    assert "signature" in (evidence.reject_reason or "")


async def test_check_2_unregistered_device_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await decide(
        db_session, await submit(db_session, world, phone, s3, device_id="never-registered")
    )
    assert evidence.status == "rejected"
    assert "not registered" in (evidence.reject_reason or "")


async def test_check_2_revoked_device_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await submit(db_session, world, phone, s3)
    device = await service.get_device(db_session, phone.device_id)
    assert device is not None
    await service.revoke_device(db_session, world.supervisor, device.id)
    result = await decide(db_session, evidence)
    assert result.status == "rejected"
    assert "revoked" in (result.reject_reason or "")


# 3. device owner and project party


async def test_check_3_device_owned_by_someone_else_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    contractor_phone = await register_phone(db_session, world.contractor)
    # The supervisor uploads using the contractor's registered phone.
    evidence = await submit(db_session, world, contractor_phone, s3, user=world.supervisor)
    result = await decide(db_session, evidence)
    assert result.status == "rejected"
    assert "different user" in (result.reject_reason or "")


async def test_check_3_uploader_who_left_the_project_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await submit(db_session, world, phone, s3)
    world.project.supervisor_id = (await make_user(db_session, "supervisor")).id  # replaced by someone else
    await db_session.flush()
    result = await decide(db_session, evidence)
    assert result.status == "rejected"
    assert "not a party" in (result.reject_reason or "")


# 4. clock


async def test_check_4_clock_more_than_10_minutes_from_gps_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    taken = datetime.now(UTC) - timedelta(minutes=2)
    evidence = await submit(
        db_session, world, phone, s3, captured_at=taken, gps_time=taken - timedelta(minutes=11)
    )
    result = await decide(db_session, evidence)
    assert result.status == "rejected"
    assert "GPS" in (result.reject_reason or "")


async def test_check_4_clock_within_10_minutes_of_gps_is_accepted(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    taken = datetime.now(UTC) - timedelta(minutes=12)
    evidence = await submit(
        db_session, world, phone, s3, captured_at=taken, gps_time=taken - timedelta(minutes=9)
    )
    assert (await decide(db_session, evidence)).status == "accepted"


async def test_check_4_upload_after_72_hours_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await submit(db_session, world, phone, s3, captured_at=datetime.now(UTC) - timedelta(hours=73))
    result = await decide(db_session, evidence)
    assert result.status == "rejected"
    assert "72 hours" in (result.reject_reason or "")


async def test_check_4_upload_just_inside_72_hours_is_accepted(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await submit(db_session, world, phone, s3, captured_at=datetime.now(UTC) - timedelta(hours=71))
    assert (await decide(db_session, evidence)).status == "accepted"


async def test_check_4_a_capture_time_in_the_future_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await submit(db_session, world, phone, s3, captured_at=datetime.now(UTC) + timedelta(hours=1))
    result = await decide(db_session, evidence)
    assert result.status == "rejected"
    assert "future" in (result.reject_reason or "")


# 5. geofence


async def test_check_5_photo_outside_the_site_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    lat = NORTH_EDGE_LAT + 50 / M_PER_DEG_LAT
    evidence = await decide(db_session, await submit(db_session, world, phone, s3, lat=lat, lon=7.5139))
    assert evidence.status == "rejected"
    assert "outside the site" in (evidence.reject_reason or "")


async def test_check_5_photo_20_m_outside_is_accepted_by_the_buffer(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    lat = NORTH_EDGE_LAT + 20 / M_PER_DEG_LAT
    evidence = await decide(db_session, await submit(db_session, world, phone, s3, lat=lat, lon=7.5139))
    assert evidence.status == "accepted"


async def test_check_5_project_without_a_site_is_flagged_for_ops(
    db_session: AsyncSession, phone: Phone, s3: Any
) -> None:
    bare = await make_world(db_session)  # no site set
    bare_phone = await register_phone(db_session, bare.supervisor)
    evidence = await decide(db_session, await submit(db_session, bare, bare_phone, s3))
    assert evidence.status == "flagged"
    assert "no site" in (evidence.reject_reason or "")


# 6. reuse


async def test_check_6_a_reused_photo_is_flagged(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    first = await decide(db_session, await submit(db_session, world, phone, s3, photo(3)))
    assert first.status == "accepted"
    again = await decide(db_session, await submit(db_session, world, phone, s3, photo(3)))
    assert again.status == "flagged"
    assert str(first.id) in (again.reject_reason or "")


async def test_check_6_a_resized_copy_is_flagged(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    original = photo(4)
    assert (
        await decide(db_session, await submit(db_session, world, phone, s3, original))
    ).status == "accepted"
    copy = await decide(db_session, await submit(db_session, world, phone, s3, resized(original)))
    assert copy.status == "flagged"


async def test_check_6_a_different_photo_is_accepted(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    a, b = photo(5), photo(6)
    assert hashing.hamming(hashing.compute_phash(a), hashing.compute_phash(b)) > hashing.REUSE_MAX_DISTANCE
    assert (await decide(db_session, await submit(db_session, world, phone, s3, a))).status == "accepted"
    assert (await decide(db_session, await submit(db_session, world, phone, s3, b))).status == "accepted"


async def test_reuse_is_found_across_projects(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    other = await make_world(db_session)
    await projects.set_site(
        db_session,
        other.ops,
        other.project.id,
        SiteSet(location=Pin(lat=INSIDE[0], lon=INSIDE[1]), geofence=FENCE),
    )
    other_phone = await register_phone(db_session, other.supervisor)
    shared = photo(7)
    assert (await decide(db_session, await submit(db_session, world, phone, s3, shared))).status == "accepted"
    assert (
        await decide(db_session, await submit(db_session, other, other_phone, s3, shared))
    ).status == "flagged"


async def test_an_unreadable_image_is_rejected(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await decide(db_session, await submit(db_session, world, phone, s3, b"not a jpeg at all"))
    assert evidence.status == "rejected"
    assert "could not be read" in (evidence.reject_reason or "")


# order of the checks: the first failure decides


async def test_the_first_failing_check_decides(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    # Outside the site AND a bad clock: the clock (check 4) comes before the geofence (check 5).
    taken = datetime.now(UTC) - timedelta(minutes=2)
    lat = NORTH_EDGE_LAT + 500 / M_PER_DEG_LAT
    evidence = await submit(
        db_session, world, phone, s3, lat=lat, captured_at=taken, gps_time=taken - timedelta(minutes=30)
    )
    result = await decide(db_session, evidence)
    assert result.status == "rejected"
    assert "GPS" in (result.reject_reason or "")


# running twice is safe


async def test_running_the_checks_twice_changes_nothing(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await submit(db_session, world, phone, s3)
    first = await decide(db_session, evidence)
    second = await decide(db_session, evidence)
    assert first.status == second.status == "accepted"
    entries = list(await db_session.scalars(select(AuditEntry).where(AuditEntry.object_id == evidence.id)))
    assert [e.action for e in entries].count("evidence.accepted") == 1


async def test_a_decision_made_by_ops_is_not_overwritten(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any
) -> None:
    evidence = await submit(db_session, world, phone, s3)
    evidence.status = "rejected"
    evidence.reject_reason = "Ops: blurry"
    await db_session.flush()
    result = await decide(db_session, evidence)
    assert result.status == "rejected" and result.reject_reason == "Ops: blurry"


async def test_unknown_evidence_is_404(db_session: AsyncSession) -> None:
    from app.core.errors import AppError

    with pytest.raises(AppError) as err:
        await checks.run_checks(db_session, uuid.uuid4())
    assert err.value.status_code == 404


# video: every 2-second keyframe is compared


def video(seeds: list[int], tmp_path: Path) -> bytes:
    """A small MP4 whose frames are the given pictures, one every 2 seconds."""
    import cv2
    import numpy as np

    path = tmp_path / f"{uuid.uuid4()}.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 1.0, (256, 256))  # type: ignore[attr-defined]
    if not writer.isOpened():
        pytest.skip("this machine's OpenCV cannot write MP4")
    for seed in seeds:
        frame = cv2.cvtColor(np.array(Image.open(io.BytesIO(photo(seed)))), cv2.COLOR_RGB2BGR)
        for _ in range(2):  # 1 frame per second, 2 seconds per picture
            writer.write(frame)
    writer.release()
    return path.read_bytes()


async def test_a_new_video_is_accepted_and_a_reused_keyframe_flags_it(
    db_session: AsyncSession, world: World, phone: Phone, s3: Any, tmp_path: Path
) -> None:
    first = await decide(
        db_session, await submit(db_session, world, phone, s3, video([11, 10], tmp_path), kind="video")
    )
    assert first.status == "accepted"
    # A different video that starts with the same picture.
    second = await decide(
        db_session, await submit(db_session, world, phone, s3, video([11, 12], tmp_path), kind="video")
    )
    assert second.status == "flagged"
    assert str(first.id) in (second.reject_reason or "")
