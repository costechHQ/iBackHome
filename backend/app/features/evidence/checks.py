"""The server checks that decide whether a capture is trusted. Owner: Abigail.

Run in this order; the first failure decides (spec, "Evidence integrity"):

    1. file hash    the stored file's SHA-256 equals the one the device signed       -> rejected
    2. signature    valid for the registered, non-revoked device key                 -> rejected
    3. device owner the device belongs to the uploader, who is on the project        -> rejected
    4. clock        captured_at within 10 min of GPS time; uploaded within 72 h      -> rejected
    5. geofence     inside the site fence plus a 25 m buffer                         -> rejected
    6. reuse        pHash within Hamming distance 8 of any stored image or video     -> flagged

If the project has no site yet the geofence cannot be judged, so the capture is flagged for ops
instead of being rejected. Everything passing means accepted. The server decides: the phone only warns.
"""

import asyncio
import hashlib
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.geo import service as geo
from app.base.users import service as users
from app.core.errors import AppError
from app.features.evidence import hashing, storage
from app.features.evidence.models import Evidence, EvidenceKind, EvidenceStatus
from app.features.evidence.service import get_device
from app.features.evidence.signing import canonical_payload, verify_signature
from app.features.projects import service as projects

MAX_CLOCK_DRIFT = timedelta(minutes=10)
MAX_UPLOAD_DELAY = timedelta(hours=72)


@dataclass(frozen=True)
class Verdict:
    status: str  # accepted | rejected | flagged
    reason: str | None = None
    phash: int | None = None


def _reject(reason: str, phash: int | None = None) -> Verdict:
    return Verdict(EvidenceStatus.REJECTED.value, reason, phash)


async def judge(session: AsyncSession, evidence: Evidence) -> Verdict:
    """Run every check in order and return the first failure, or `accepted`."""
    data = await asyncio.to_thread(storage.read_object, evidence.storage_key)
    if data is None:
        return _reject("The uploaded file is missing from storage.")

    # 1. file hash
    if hashlib.sha256(data).hexdigest() != evidence.file_sha256:
        return _reject("The file does not match the hash the device signed.")

    # 2. signature
    device = await get_device(session, evidence.device_id)
    if device is None:
        return _reject("The device is not registered.")
    if device.revoked_at is not None:
        return _reject("The device key has been revoked.")
    try:
        payload = canonical_payload(
            evidence.file_sha256,
            evidence.captured_at,
            evidence.gps_time,
            evidence.latitude,
            evidence.longitude,
            evidence.accuracy_m,
            evidence.project_id,
            evidence.device_id,
        )
    except AppError as exc:
        return _reject(f"The capture details are invalid: {exc.message}")
    if not verify_signature(device.public_key, payload, evidence.signature, revoked_at=device.revoked_at):
        return _reject("The signature is not valid for this device.")

    # 3. device owner and project party
    if device.user_id != evidence.captured_by:
        return _reject("The device belongs to a different user.")
    uploader = await users.get_user(session, evidence.captured_by)
    project = await projects.get_project(session, evidence.project_id)
    if uploader is None or not projects.is_member(uploader, project):
        return _reject("The uploader is not a party to this project.")

    # 4. clock
    if abs(evidence.captured_at - evidence.gps_time) > MAX_CLOCK_DRIFT:
        return _reject("The phone's clock differs from GPS time by more than 10 minutes.")
    if evidence.captured_at > evidence.created_at + MAX_CLOCK_DRIFT:
        return _reject("The capture time is in the future.")
    if evidence.created_at - evidence.captured_at > MAX_UPLOAD_DELAY:
        return _reject("The capture was uploaded more than 72 hours after it was taken.")

    # 5. geofence
    try:
        fence = await projects.get_project_geofence(session, evidence.project_id)
    except AppError as exc:
        if exc.code != "site_not_set":
            raise
        return Verdict(EvidenceStatus.FLAGGED.value, "The project has no site geofence yet; ops must review.")
    if not await geo.inside_geofence(session, fence, evidence.latitude, evidence.longitude):
        metres = await geo.distance_to_fence(session, fence, evidence.latitude, evidence.longitude)
        return _reject(f"The capture was taken {metres:.0f} m outside the site.")

    # 6. reuse
    try:
        fingerprints = await asyncio.to_thread(_fingerprints, evidence.kind, data)
    except (ValueError, OSError):
        return _reject("The file could not be read as a photo or video.")
    if not fingerprints:
        return _reject("The file could not be read as a photo or video.")
    for phash in fingerprints:
        match = await hashing.check_reuse(session, phash, exclude_evidence_id=evidence.id)
        if match is not None:
            return Verdict(
                EvidenceStatus.FLAGGED.value,
                f"Looks like evidence {match.evidence_id} (distance {match.distance}); ops must review.",
                fingerprints[0],
            )
    return Verdict(EvidenceStatus.ACCEPTED.value, None, fingerprints[0])


def _fingerprints(kind: str, data: bytes) -> list[int]:
    """One pHash for a photo, one per 2-second keyframe for a video (an unreadable file gives [])."""
    if kind == EvidenceKind.PHOTO.value:
        try:
            return [hashing.compute_phash(data)]
        except Exception as exc:  # PIL raises many types for a corrupt image
            raise ValueError("unreadable image") from exc
    handle, path = tempfile.mkstemp(suffix=".mp4")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        return hashing.video_phashes(path)
    finally:
        os.unlink(path)


async def run_checks(session: AsyncSession, evidence_id: uuid.UUID) -> Evidence:
    """Judge one capture and save the result. Safe to run twice: only `pending_checks` is judged."""
    from sqlalchemy import select

    from app.base import audit

    evidence = await session.scalar(
        select(Evidence)
        .where(Evidence.id == evidence_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if evidence is None:
        raise AppError("evidence_not_found", "Evidence not found.", 404)
    if evidence.status != EvidenceStatus.PENDING_CHECKS.value:
        return evidence  # already decided (a second run, or ops got there first)

    before = audit.snapshot(evidence)
    verdict = await judge(session, evidence)
    evidence.status = verdict.status
    evidence.reject_reason = verdict.reason
    if verdict.phash is not None:
        evidence.phash = verdict.phash
    await session.flush()
    await session.refresh(evidence)
    await audit.record(
        session,
        None,  # the system decides
        f"evidence.{verdict.status}",
        "evidence",
        evidence.id,
        before=before,
        after=audit.snapshot(evidence),
    )
    return evidence


async def flag_unchecked(session: AsyncSession, evidence_id: uuid.UUID, reason: str) -> Evidence:
    """Last resort when the checks cannot run: send a still-pending capture to ops (no verdict invented)."""
    from sqlalchemy import select

    from app.base import audit

    evidence = await session.scalar(
        select(Evidence)
        .where(Evidence.id == evidence_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if evidence is None:
        raise AppError("evidence_not_found", "Evidence not found.", 404)
    if evidence.status != EvidenceStatus.PENDING_CHECKS.value:
        return evidence
    before = audit.snapshot(evidence)
    evidence.status = EvidenceStatus.FLAGGED.value
    evidence.reject_reason = reason
    await session.flush()
    await session.refresh(evidence)
    await audit.record(
        session,
        None,
        "evidence.flagged",
        "evidence",
        evidence.id,
        before=before,
        after=audit.snapshot(evidence),
    )
    return evidence
