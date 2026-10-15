"""Business rules for evidence: devices, uploads and submitted captures. Owner: Abigail.

Other features call the functions in this file; they never query this feature's tables directly.
Every function takes the database session as its first argument.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import audit
from app.base.users.models import User
from app.core import pagination
from app.core.errors import AppError
from app.features.evidence import media, storage
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
        upload_url=await asyncio.to_thread(storage.presign_upload, key, data.content_type),
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

    stored = await asyncio.to_thread(storage.head_object, data.storage_key)
    if stored is None:
        raise AppError("file_not_uploaded", "Upload the file to the upload URL first.", 422)
    size, content_type = stored
    if content_type != CONTENT_TYPES[data.kind]:
        raise AppError("invalid_content_type", f"A {data.kind} must be {CONTENT_TYPES[data.kind]}.", 422)
    if size > MAX_BYTES[data.kind]:
        await asyncio.to_thread(
            storage.delete_object, data.storage_key
        )  # a presigned PUT can't cap the size, so enforce it here
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
        gps_time=data.gps_time,
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


# --- Gallery -----------------------------------------------------------------------------------

READ_URL_TTL_S = storage.READ_URL_TTL_S


@dataclass(frozen=True)
class GalleryEntry:
    evidence: Evidence
    read_url: str
    is_client_copy: bool


def _view_url(evidence: Evidence, *, for_client: bool) -> tuple[str, bool]:
    if for_client and evidence.kind == EvidenceKind.PHOTO.value:
        return media.client_copy_url(evidence.storage_key), True
    # Videos have no EXIF stripper yet, so a client gets the original video link.
    return storage.presign_read(evidence.storage_key), False


async def list_gallery(
    session: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    *,
    milestone_id: uuid.UUID | None = None,
    status: str | None = None,
    kind: str | None = None,
    captured_by_role: str | None = None,
    cursor: str | None = None,
    limit: int = pagination.DEFAULT_LIMIT,
) -> tuple[list[GalleryEntry], str | None]:
    """A project's evidence, newest first, with 15-minute read URLs. Members and ops only.

    A client sees only `accepted` evidence, as stripped copies. Everyone else sees every status.
    """
    await projects.require_project_member(session, user, project_id)
    query = select(Evidence).where(Evidence.project_id == project_id)
    for_client = user.role == "client"
    if for_client:
        query = query.where(Evidence.status == EvidenceStatus.ACCEPTED.value)
    if milestone_id is not None:
        query = query.where(Evidence.milestone_id == milestone_id)
    if status is not None:
        query = query.where(Evidence.status == status)
    if kind is not None:
        query = query.where(Evidence.kind == kind)
    if captured_by_role is not None:
        query = query.where(Evidence.captured_by_role == captured_by_role)
    if cursor is not None:
        at, row_id = pagination.decode_cursor(cursor)
        query = query.where(tuple_(Evidence.created_at, Evidence.id) < tuple_(at, row_id))
    rows = list(
        await session.scalars(query.order_by(Evidence.created_at.desc(), Evidence.id.desc()).limit(limit + 1))
    )
    page, next_cursor = pagination.page(rows, limit, lambda e: (e.created_at, e.id))
    entries = []
    for evidence in page:
        url, is_copy = await asyncio.to_thread(_view_url, evidence, for_client=for_client)
        entries.append(GalleryEntry(evidence, url, is_copy))
    return entries, next_cursor


# --- Ops decisions on flagged evidence ---------------------------------------------------------

# The only moves ops can make on evidence (anything else is a 409): flagged -> accepted or rejected.
OPS_DECISIONS = {EvidenceStatus.ACCEPTED.value, EvidenceStatus.REJECTED.value}


async def decide_flagged(
    session: AsyncSession,
    ops: User,
    evidence_id: uuid.UUID,
    decision: str,
    notes: str,
    request: Request | None = None,
) -> Evidence:
    """Ops accept or reject evidence the server flagged (a reused image, or a project with no site)."""
    if decision not in OPS_DECISIONS:
        raise AppError("invalid_decision", "Decide accepted or rejected.", 422)
    notes = notes.strip()
    if decision == EvidenceStatus.REJECTED.value and not notes:
        raise AppError("notes_required", "Say why you are rejecting this evidence.", 422)
    evidence = await session.scalar(
        select(Evidence)
        .where(Evidence.id == evidence_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if evidence is None:
        raise AppError("evidence_not_found", "Evidence not found.", 404)
    if evidence.status != EvidenceStatus.FLAGGED.value:
        raise AppError(
            "invalid_evidence_transition",
            f"Only flagged evidence can be decided by ops; this is {evidence.status}.",
            409,
        )
    before = audit.snapshot(evidence)
    evidence.status = decision
    evidence.reject_reason = f"Ops: {notes}" if decision == EvidenceStatus.REJECTED.value else None
    await session.flush()
    await session.refresh(evidence)
    await audit.record(
        session,
        ops.id,
        f"evidence.ops_{decision}",
        "evidence",
        evidence.id,
        before=before,
        after={**audit.snapshot(evidence), "ops_notes": notes},
        request=request,
    )
    return evidence


async def list_flagged(session: AsyncSession, limit: int = 100) -> list[Evidence]:
    """Flagged evidence waiting for ops, oldest first (for the ops queue)."""
    rows = await session.scalars(
        select(Evidence)
        .where(Evidence.status == EvidenceStatus.FLAGGED.value)
        .order_by(Evidence.created_at, Evidence.id)
        .limit(limit)
    )
    return list(rows)


async def accepted_supervisor_evidence_count(
    session: AsyncSession, project_id: uuid.UUID, evidence_ids: list[uuid.UUID]
) -> int:
    """How many of these ids are accepted evidence on this project taken by its supervisor."""
    rows = await session.scalars(
        select(Evidence.id).where(
            Evidence.id.in_(evidence_ids),
            Evidence.project_id == project_id,
            Evidence.status == EvidenceStatus.ACCEPTED.value,
            Evidence.captured_by_role == "supervisor",
        )
    )
    return len(set(rows))
