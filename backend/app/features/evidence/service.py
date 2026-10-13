"""Business rules for evidence devices. Owner: Abigail.

Other features call the functions in this file; they never query this feature's tables directly.
Every function takes the database session as its first argument.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.evidence.models import Device
from app.features.evidence.signing import SEPARATOR, is_valid_public_key


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
