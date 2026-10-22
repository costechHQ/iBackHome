"""Request and response shapes (Pydantic) for users. Owner: Christopher."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_IDENTIFIER = Field(
    min_length=3,
    max_length=254,
    description=(
        "Phone number (Nigerian local such as 0803..., or any country with its code, such as +44...) "
        "or email address."
    ),
)


class OtpRequestIn(BaseModel):
    identifier: str = _IDENTIFIER
    channel: Literal["sms", "whatsapp", "email"] | None = Field(
        default=None,
        description="How to send the code: sms (default) or whatsapp for a phone number, email for an email.",
    )


class OtpRequestOut(BaseModel):
    status: str = "sent"
    expires_in: int = Field(description="Seconds until the code expires.")


class OtpVerifyIn(BaseModel):
    identifier: str = _IDENTIFIER
    code: str = Field(pattern=r"^\d{6}$", description="The 6-digit code that was sent.")


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type name, not a secret
    expires_in: int = Field(description="Seconds until the access token expires.")


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str | None
    email: str | None
    full_name: str | None
    role: str
    status: str
    timezone: str
    country: str | None
    consented_at: datetime | None = None
    consent_required: bool = Field(
        default=False,
        description="True until the person agrees to the current terms of use and privacy policy.",
    )


class MeUpdate(BaseModel):
    """PATCH /me: only the fields sent change. Phone and email are sign-in identifiers, not changed here."""

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$", description="ISO 3166-1 alpha-2")
    timezone: str | None = Field(
        default=None, min_length=1, max_length=64, description="IANA, e.g. Europe/London"
    )


class ConsentIn(BaseModel):
    """The versions the person saw and agreed to; they must be the current ones."""

    model_config = ConfigDict(extra="forbid")

    terms_version: str = Field(min_length=1, max_length=32)
    privacy_version: str = Field(min_length=1, max_length=32)


class ConsentOut(BaseModel):
    """The current documents to agree to, and what this person agreed to."""

    terms_version: str = Field(description="The current terms of use version")
    privacy_version: str = Field(description="The current privacy policy version")
    consented_at: datetime | None
    consent_required: bool
