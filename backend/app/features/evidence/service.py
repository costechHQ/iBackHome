"""Business rules for evidence: devices, uploads and submitted captures. Owner: Abigail.

Other features call the functions in this file; they never query this feature's tables directly.
Every function takes the database session as its first argument.
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.users.models import User
from app.core.errors import AppError
from app.features.evidence import storage
from app.features.evidence.models import Device, Evidence, EvidenceKind, EvidenceStatus
from app.features.evidence.schemas import EvidenceIn, UploadUrlOut, UploadUrlRequest
from app.features.evidence.signing import SEPARATOR, is_valid_public_key
from app.features.milestones import service as milestones
from app.features.projects import service as projects

log = logging.getLogger(__name__)

MAX_BYTES = {EvidenceKind.PHOTO.value: 10 * 1024 * 1024, EvidenceKind.VIDEO.value: 60 * 1024 * 1024}
CONTENT_TYPES = {EvidenceKind.PHOTO.value: "image/jpeg", EvidenceKind.VIDEO.value: "video/mp4"}
EXTENSIONS = {"image/jpeg": "jpg", "video/mp4": "mp4"}


# --- Devices -----------------------------------------------------------------------------------


async def register_device(
    session: AsyncSession, user_id: uuid.UUID, device_id: str, public_key: str
) -> tuple[Device, bool]:
    """Register a phone's public key. Returns (device, created).

    Sending the same device_id and key again for the same user returns the existing row, so a
    retry never makes a duplicate. Reusing a device_id with another key or user is a 409.
    """
    if SEPARATOR in device_id or "\n" in device_id or "\r" in device_id or not device_id.strip():
        raise AppError("invalid_device", 'device_id must not be blank or contain "|" or line breaks.', 422)
    if not is_valid_public_key(public_key):
        raise AppError("invalid_public_key", "public_key must be a base64 X.509 ECDSA P-256 public key.", 422)

    existing = await session.scalar(select(Device).where(Device.device_id == device_id))
    if existing is not None:
        if existing.user_id != user_id or existing.public_key != public_key:
            raise AppError("device_id_taken", "This device_id is already registered.", 409)
        if existing.revoked_at is not None:
            raise AppError("device_revoked", "This device was revoked; register a new device_id.", 409)
        return existing, False

    device = Device(user_id=user_id, device_id=device_id, public_key=public_key)
    session.add(device)
    await session.flush()
    await session.refresh(device)
    return device, True


async def revoke_device(session: AsyncSession, device_pk: uuid.UUID) -> Device:
    """Revoke a device (ops only, checked by the router). Revoking twice keeps the first time."""
    device = await session.get(Device, device_pk)
    if device is None:
        raise AppError("device_not_found", "This device does not exist.", 404)
    if device.revoked_at is None:
        device.revoked_at = datetime.now(UTC)
        await session.flush()
    return device


async def get_device(session: AsyncSession, device_id: str) -> Device | None:
    """Look a device up by its device_id (used by the evidence checks)."""
    return await session.scalar(select(Device).where(Device.device_id == device_id))


# --- Uploads -----------------------------------------------------------------------------------


def _key_prefix(project_id: uuid.UUID) -> str:
    return f"evidence/{project_id}/"


async def create_upload_url(session: AsyncSession, user: User, data: UploadUrlRequest) -> UploadUrlOut:
    """A 15-minute pre-signed PUT URL for one file. The caller must be on the project."""
    await projects.require_project_member(session, user, data.project_id)
    if CONTENT_TYPES[data.kind] != data.content_type:
        raise AppError(
            "invalid_content_type", f"A {data.kind} must be uploaded as {CONTENT_TYPES[data.kind]}.", 422
        )
    key = f"{_key_prefix(data.project_id)}{uuid.uuid4()}.{EXTENSIONS[data.content_type]}"
    return UploadUrlOut(
        storage_key=key,
        upload_url=storage.presign_upload(key, data.content_type),
        headers={"Content-Type": data.content_type},
        expires_in=storage.UPLOAD_URL_TTL_S,
        max_bytes=MAX_BYTES[data.kind],
    )


def enqueue_run_checks(evidence_id: uuid.UUID) -> None:
    """Queue the server checks. A queue outage must not lose the upload, so it only logs."""
    from app.features.evidence.tasks import run_checks

    try:
        run_checks.delay(str(evidence_id))
    except Exception:
        log.exception("could not queue run_checks for evidence %s", evidence_id)


async def submit_evidence(
    session: AsyncSession, user: User, data: EvidenceIn, request: Request | None = None
) -> tuple[Evidence, bool]:
    """Save a capture's metadata and signature as `pending_checks`. Returns (evidence, created).

    The file must already be uploaded to `data.storage_key`. Nothing is judged here: the hash,
    signature, clock, geofence and reuse checks run later (run_checks) and set the final status.
    Sending the same storage_key again returns the saved row, so a retry never duplicates.
    """
    await projects.require_project_member(session, user, data.project_id)
    if not data.storage_key.startswith(_key_prefix(data.project_id)):
        raise AppError("invalid_storage_key", "storage_key does not belong to this project.", 422)

    existing = await session.scalar(select(Evidence).where(Evidence.storage_key == data.storage_key))
    if existing is not None:
        if existing.captured_by != user.id:
            raise AppError("storage_key_taken", "This file was submitted by someone else.", 409)
        return existing, False

    if data.milestone_id is not None:
        milestone = await milestones.get_milestone(session, data.milestone_id)
        if milestone.project_id != data.project_id:
            raise AppError("milestone_not_in_project", "This milestone is not on this project.", 422)

    stored = storage.head_object(data.storage_key)
    if stored is None:
        raise AppError("file_not_uploaded", "Upload the file to the upload URL first.", 422)
    size, content_type = stored
    if content_type != CONTENT_TYPES[data.kind]:
        raise AppError("invalid_content_type", f"A {data.kind} must be {CONTENT_TYPES[data.kind]}.", 422)
    if size > MAX_BYTES[data.kind]:
        storage.delete_object(data.storage_key)  # a presigned PUT can't cap the size, so enforce it here
        raise AppError(
            "file_too_large", f"A {data.kind} can be at most {MAX_BYTES[data.kind] // (1024 * 1024)} MB.", 422
        )

    evidence = Evidence(
        project_id=data.project_id,
        milestone_id=data.milestone_id,
        captured_by=user.id,
        captured_by_role=user.role,
        kind=data.kind,
        storage_key=data.storage_key,
        content_type=content_type,
        size_bytes=size,
        file_sha256=data.file_sha256,
        captured_at=data.captured_at,
        latitude=data.latitude,
        longitude=data.longitude,
        accuracy_m=data.accuracy_m,
        device_id=data.device_id,
        signature=data.signature,
        status=EvidenceStatus.PENDING_CHECKS.value,
    )
    session.add(evidence)
    await session.flush()
    await session.refresh(evidence)
    await audit.record(
        session,
        user.id,
        "evidence.submitted",
        "evidence",
        evidence.id,
        after=audit.snapshot(evidence),
        request=request,
    )
    return evidence, True


async def accepted_for_milestone(session: AsyncSession, milestone_id: uuid.UUID) -> list[Evidence]:
    """Evidence that counts toward verifying a milestone: accepted, and captured by the supervisor.

    Contractor uploads never count, and neither do pending, flagged or rejected ones.
    Used by milestones (verify needs the checklist's number of photos).
    """
    rows = await session.scalars(
        select(Evidence)
        .where(
            Evidence.milestone_id == milestone_id,
            Evidence.status == EvidenceStatus.ACCEPTED.value,
            Evidence.captured_by_role == "supervisor",
        )
        .order_by(Evidence.captured_at, Evidence.id)
    )
    return list(rows)
