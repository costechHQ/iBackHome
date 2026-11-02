"""A supervisor's NIN, held only while their application is pending. Owner: James.

The National Identification Number is personal data (NDPA 2023). Ops need the full number to check it, so it
is kept encrypted (Fernet) until they approve or reject, and is then wiped: only the last 4 digits stay
(design: "only the last 4 NIN digits are kept after the check"). It is never logged, never written to the
audit log (the column is excluded from audit snapshots) and never sent to anyone but ops, once, while pending.

The key is `NIN_ENCRYPTION_KEY`: any random string of 32 or more characters (the Fernet key is derived).
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.errors import AppError

MIN_KEY_CHARS = 32
NIN_DIGITS = 11


def _fernet() -> Fernet:
    key = get_settings().nin_encryption_key
    if len(key) < MIN_KEY_CHARS:
        raise AppError(
            "nin_not_configured",
            "We can't take a NIN right now. Please try again later.",
            503,
        )
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))


def is_nin(value: str) -> bool:
    return len(value) == NIN_DIGITS and value.isascii() and value.isdigit()


def encrypt(nin: str) -> str:
    """The NIN as an encrypted token. 503 nin_not_configured when there is no key."""
    return _fernet().encrypt(nin.encode()).decode()


def decrypt(token: str) -> str | None:
    """The NIN back, or None if the key has changed since it was stored (the applicant must send it again)."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None
