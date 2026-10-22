"""HTTP endpoints for login and the current user. Owner: Christopher.

Routes are mounted under /api/v1 automatically; parse the request, check permissions,
call service.py, and return a schema. Keep business rules out of this file.
"""

import hashlib
from typing import Any

from fastapi import APIRouter, Request, Response

from app.base.users import service
from app.base.users.models import User
from app.base.users.otp_sender import OtpSenderDep
from app.base.users.schemas import (
    ConsentIn,
    ConsentOut,
    MeOut,
    MeUpdate,
    OtpRequestIn,
    OtpRequestOut,
    OtpVerifyIn,
    RefreshIn,
    TokenPair,
)
from app.core.config import get_settings
from app.core.db import SessionDep
from app.core.idempotency import IdempotencyKeyDep, remember, replay_or_none

router = APIRouter(tags=["users"])


def _client_ip(request: Request) -> str:
    # The direct peer, or the caller from X-Forwarded-For when the peer is a proxy listed in
    # FORWARDED_ALLOW_IPS (uvicorn --proxy-headers). Set it on staging/production, or every caller
    # looks like the proxy; never "*" unless the API is reachable only through the proxy.
    return request.client.host if request.client else "unknown"


@router.post("/auth/otp/request", status_code=202, response_model=OtpRequestOut)
async def request_otp(
    payload: OtpRequestIn,
    request: Request,
    session: SessionDep,
    sender: OtpSenderDep,
    key: IdempotencyKeyDep,
) -> Any:
    # The scope holds a hash of the identifier, never the phone or email itself.
    who = hashlib.sha256(payload.identifier.strip().lower().encode()).hexdigest()[:32]
    scope = f"POST /auth/otp/request {who} {payload.channel or 'default'}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    expires_in = await service.request_otp(
        session, payload.identifier, _client_ip(request), sender, channel=payload.channel
    )
    body = OtpRequestOut(expires_in=expires_in).model_dump(mode="json")
    await remember(session, key, scope, 202, body)
    await session.commit()
    return body


# verify and refresh accept Idempotency-Key but never store their responses: they contain live
# tokens, and both are single-use anyway (the code is consumed, the refresh token is rotated).


@router.post("/auth/otp/verify", response_model=TokenPair)
async def verify_otp(
    payload: OtpVerifyIn, response: Response, session: SessionDep, _key: IdempotencyKeyDep
) -> TokenPair:
    response.headers["Cache-Control"] = "no-store"
    return await service.verify_otp(session, payload.identifier, payload.code)


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshIn, response: Response, session: SessionDep, _key: IdempotencyKeyDep
) -> TokenPair:
    response.headers["Cache-Control"] = "no-store"
    return await service.rotate_refresh_token(session, payload.refresh_token)


def _me(user: User) -> MeOut:
    return MeOut.model_validate(user).model_copy(update={"consent_required": service.consent_required(user)})


@router.get("/me", response_model=MeOut)
async def me(user: service.CurrentUserDep) -> MeOut:
    return _me(user)


@router.patch("/me", response_model=MeOut)
async def update_me(
    payload: MeUpdate,
    request: Request,
    session: SessionDep,
    user: service.CurrentUserDep,
    key: IdempotencyKeyDep,
) -> Any:
    """The signed-in person changes their own name, country or time zone (only the fields sent)."""
    scope = f"PATCH /me {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    await service.update_profile(session, user, payload.model_dump(exclude_unset=True), request)
    body = _me(user).model_dump(mode="json")
    await remember(session, key, scope, 200, body)
    await session.commit()
    return body


def _consent(user: User) -> ConsentOut:
    settings = get_settings()
    return ConsentOut(
        terms_version=settings.terms_version,
        privacy_version=settings.privacy_version,
        consented_at=user.consented_at,
        consent_required=service.consent_required(user, settings),
    )


@router.get("/me/consent", response_model=ConsentOut)
async def consent(user: service.CurrentUserDep) -> ConsentOut:
    """The terms of use and privacy policy versions to agree to (NDPA 2023), and whether this person has."""
    return _consent(user)


@router.post("/me/consent", response_model=ConsentOut)
async def give_consent(
    payload: ConsentIn,
    request: Request,
    session: SessionDep,
    user: service.CurrentUserDep,
    key: IdempotencyKeyDep,
) -> Any:
    """The person agrees to the current versions; older ones get 409 consent_version_outdated."""
    scope = f"POST /me/consent {user.id}"
    if (saved := await replay_or_none(session, key, scope)) is not None:
        return saved
    await service.record_consent(session, user, payload.terms_version, payload.privacy_version, request)
    body = _consent(user).model_dump(mode="json")
    await remember(session, key, scope, 200, body)
    await session.commit()
    return body
