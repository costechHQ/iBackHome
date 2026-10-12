"""Device signatures for evidence: the canonical payload and ECDSA P-256 verification.

The phone signs `canonical_payload(...)` with a key that never leaves its Keystore; the server
rebuilds the same bytes from the submitted metadata and checks the signature. The exact format
is documented in SIGNING.md and is the contract for the Flutter phase: change both together.
"""

import base64
import binascii
import re
import uuid
from datetime import UTC, datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.errors import AppError

PAYLOAD_VERSION = "ibh-evidence-v1"
SEPARATOR = "|"
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def _bad(message: str) -> AppError:
    return AppError("invalid_capture_metadata", message, 422)


def canonical_payload(
    file_sha256: str,
    captured_at: datetime,
    lat: float,
    lon: float,
    accuracy_m: float,
    project_id: uuid.UUID | str,
    device_id: str,
) -> bytes:
    """The exact bytes the device signs, fields joined with "|" in this fixed order:

    ibh-evidence-v1 | file_sha256 | captured_at | lat | lon | accuracy_m | project_id | device_id

    - file_sha256: 64 lowercase hex characters (SHA-256 of the uploaded file bytes)
    - captured_at: UTC, ISO 8601 with milliseconds and a trailing Z, e.g. 2026-10-12T09:30:15.123Z
    - lat, lon: fixed 6 decimals (the device rounds to 6 decimals before signing and sending)
    - accuracy_m: fixed 1 decimal
    - project_id: lowercase hyphenated UUID
    - device_id: the registered device id, as registered (must not contain "|")
    """
    if not _SHA256_HEX.fullmatch(file_sha256):
        raise _bad("file_sha256 must be 64 lowercase hex characters.")
    if captured_at.tzinfo is None:
        raise _bad("captured_at must include a timezone.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise _bad("Latitude or longitude is out of range.")
    if accuracy_m < 0:
        raise _bad("accuracy_m cannot be negative.")
    if not device_id or SEPARATOR in device_id or any(c in device_id for c in "\r\n"):
        raise _bad('device_id must be non-empty and must not contain "|" or line breaks.')
    try:
        project = str(uuid.UUID(str(project_id)))
    except ValueError:
        raise _bad("project_id must be a UUID.") from None

    utc = captured_at.astimezone(UTC)
    when = utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"
    fields = [
        PAYLOAD_VERSION,
        file_sha256,
        when,
        _fixed(lat, 6),
        _fixed(lon, 6),
        _fixed(accuracy_m, 1),
        project,
        device_id,
    ]
    return SEPARATOR.join(fields).encode("utf-8")


def _fixed(value: float, places: int) -> str:
    text = f"{value:.{places}f}"
    return text[1:] if text.startswith("-") and float(text) == 0 else text  # no "-0.000000"


def is_valid_public_key(public_key: str) -> bool:
    """True if `public_key` is base64 X.509 SubjectPublicKeyInfo DER holding an ECDSA P-256 key."""
    try:
        key = serialization.load_der_public_key(base64.b64decode(public_key, validate=True))
    except (ValueError, binascii.Error, TypeError):
        return False
    return isinstance(key, ec.EllipticCurvePublicKey) and isinstance(key.curve, ec.SECP256R1)


def verify_signature(
    public_key: str,
    payload: bytes,
    signature: str,
    *,
    revoked_at: datetime | None = None,
) -> bool:
    """True only if `signature` is a valid ECDSA P-256 / SHA-256 signature of `payload`.

    public_key: base64 of the X.509 SubjectPublicKeyInfo DER (what Android's `publicKey.encoded` gives)
    signature:  base64 of the DER-encoded ECDSA signature (what Android's SHA256withECDSA gives)
    revoked_at: pass the device's `revoked_at`; a revoked key never verifies.
    Never raises: malformed input, a non-P-256 key or a bad signature all return False.
    """
    if revoked_at is not None:
        return False
    try:
        key = serialization.load_der_public_key(base64.b64decode(public_key, validate=True))
        if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
            return False
        key.verify(base64.b64decode(signature, validate=True), payload, ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError, binascii.Error, TypeError):
        return False
    return True
