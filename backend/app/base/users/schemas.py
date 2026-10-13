"""Request and response shapes (Pydantic) for users. Owner: Christopher."""

import uuid

from pydantic import BaseModel, ConfigDict, Field

_IDENTIFIER = Field(
    min_length=3,
    max_length=254,
    description="Phone number (Nigerian local such as 0803..., or international +...) or email address.",
)


class OtpRequestIn(BaseModel):
    identifier: str = _IDENTIFIER


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
