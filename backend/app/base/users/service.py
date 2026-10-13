"""Business rules for users: OTP login, tokens, and who is calling. Owner: Christopher.

Other modules use only these names:

    from typing import Annotated
    from fastapi import Depends
    from app.base.users import service as users
    from app.base.users.models import User

    @router.get("/things")
    async def list_things(user: users.CurrentUserDep) -> ...:          # any signed-in user
        ...

    OpsUser = Annotated[User, Depends(users.require_role("ops"))]      # one or more roles

    user = await users.get_user(session, user_id)                      # None if unknown

Every function takes the database session first. Codes and tokens are never logged or stored in
plain text: OTP codes are kept as HMAC-SHA256 (keyed with JWT_SECRET), refresh tokens as SHA-256.
"""

import hashlib
import hmac
import secrets
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
import phonenumbers
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import ColumnElement, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import OtpChannel, OtpCode, RefreshToken, Role, User, UserStatus
from app.base.users.otp_sender import OtpSender
from app.base.users.schemas import TokenPair
from app.core.config import Settings, get_settings
from app.core.db import SessionDep
from app.core.errors import AppError

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "ibackhome"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - the JWT "type" claim, not a secret
OTP_DIGITS = 6
DEFAULT_PHONE_REGION = "NG"  # "0803..." means a Nigerian number


def _utcnow() -> datetime:
    return datetime.now(UTC)


# --- Identifiers -------------------------------------------------------------------------------


PHONE_CHANNELS = frozenset({OtpChannel.SMS.value, OtpChannel.WHATSAPP.value})


def _invalid_phone() -> AppError:
    return AppError(
        "invalid_phone", "This phone number isn't valid. Check the digits and the country code.", 422
    )


def _parsed_valid(value: str, region: str | None) -> phonenumbers.PhoneNumber | None:
    try:
        number = phonenumbers.parse(value, region)
    except phonenumbers.NumberParseException:
        return None
    return number if phonenumbers.is_valid_number(number) else None


def _normalise_email(value: str) -> str:
    email = value.lower()
    local, _, domain = email.partition("@")
    if (
        email.count("@") != 1
        or not local
        or "." not in domain
        or domain.startswith(".")
        or domain.endswith(".")
        or any(c.isspace() for c in email)
        or len(email) > 254
    ):
        raise AppError("invalid_email", "Enter a valid email address.", 422)
    return email


def _normalise_phone(value: str) -> str:
    """Any country's number in E.164. Without a leading +, the number is read as Nigerian."""
    if value.startswith("+"):
        number = _parsed_valid(value, None)
    else:
        number = _parsed_valid(value, DEFAULT_PHONE_REGION)
        if number is None and _parsed_valid("+" + value, None) is not None:
            # e.g. 447400123456: a valid foreign number typed without its leading +.
            raise AppError(
                "phone_needs_country_code",
                "Numbers outside Nigeria need the country code with a leading +, "
                "for example +44 7400 123456.",
                422,
            )
    if number is None:
        raise _invalid_phone()
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def normalise_identifier(raw: str) -> tuple[str, str]:
    """Return (identifier, default channel): a lower-case email, or any phone number in E.164.

    Nigerian local numbers (0803...) become +234...; other countries need their code (+44..., +1...).
    """
    value = raw.strip()
    if "@" in value:
        return _normalise_email(value), OtpChannel.EMAIL.value
    return _normalise_phone(value), OtpChannel.SMS.value


def choose_channel(default_channel: str, requested: str | None) -> str:
    """sms (default) or whatsapp for a phone number; email for an email address."""
    if requested is None:
        return default_channel
    allowed = PHONE_CHANNELS if default_channel != OtpChannel.EMAIL.value else {OtpChannel.EMAIL.value}
    if requested not in allowed:
        raise AppError(
            "channel_mismatch",
            "Use sms or whatsapp for a phone number, and email for an email address.",
            422,
        )
    return requested


# --- Hashing -----------------------------------------------------------------------------------


def _code_hash(settings: Settings, identifier: str, code: str) -> str:
    message = f"{identifier}:{code}".encode()
    return hmac.new(settings.jwt_secret.encode(), message, hashlib.sha256).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --- Requesting a code -------------------------------------------------------------------------


async def _lock(session: AsyncSession, key: str) -> None:
    """Transaction-level advisory lock: released automatically at commit or rollback."""
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key})


async def _enforce_limit(
    session: AsyncSession,
    condition: ColumnElement[bool],
    limit: int,
    settings: Settings,
    now: datetime,
) -> None:
    window = timedelta(minutes=settings.otp_limit_window_minutes)
    count, oldest = (
        await session.execute(
            select(func.count(), func.min(OtpCode.created_at)).where(
                condition, OtpCode.created_at > now - window
            )
        )
    ).one()
    if count >= limit:
        retry_after = max(1, int((oldest + window - now).total_seconds()) + 1)
        raise HTTPException(
            429, "Too many login codes requested. Try again later.", headers={"Retry-After": str(retry_after)}
        )


async def request_otp(
    session: AsyncSession,
    raw_identifier: str,
    ip: str,
    sender: OtpSender,
    *,
    channel: str | None = None,
    now: datetime | None = None,
) -> int:
    """Create and send a new login code; returns seconds until it expires. The caller commits.

    `channel` is sms (default) or whatsapp for a phone, email for an email. Rate limits count every
    code for the identifier and the IP, whatever the channel. The response is the same whether or
    not an account exists for the identifier.
    """
    settings = get_settings()
    now = now or _utcnow()
    identifier, default_channel = normalise_identifier(raw_identifier)
    channel = choose_channel(default_channel, channel)

    # Serialise concurrent requests for the same IP, then the same identifier (always in this order,
    # so two requests can't deadlock), so the counts below can't be raced past the limits.
    await _lock(session, f"otp-ip:{ip}")
    await _lock(session, f"otp-identifier:{identifier}")
    by_identifier, by_ip = OtpCode.identifier == identifier, OtpCode.requested_ip == ip
    await _enforce_limit(session, by_identifier, settings.otp_limit_per_identifier, settings, now)
    await _enforce_limit(session, by_ip, settings.otp_limit_per_ip, settings, now)

    # Only the newest code can be used: retire any earlier one.
    await session.execute(
        update(OtpCode)
        .where(OtpCode.identifier == identifier, OtpCode.consumed_at.is_(None))
        .values(consumed_at=now)
    )
    code = f"{secrets.randbelow(10**OTP_DIGITS):0{OTP_DIGITS}d}"
    ttl = timedelta(minutes=settings.otp_ttl_minutes)
    session.add(
        OtpCode(
            identifier=identifier,
            channel=channel,
            code_hash=_code_hash(settings, identifier, code),
            expires_at=now + ttl,
            requested_ip=ip,
            created_at=now,
        )
    )
    await session.flush()
    await sender.send(identifier, channel, code)
    return int(ttl.total_seconds())


# --- Verifying a code --------------------------------------------------------------------------


async def _find_or_create_user(session: AsyncSession, identifier: str, channel: str) -> User:
    column = User.phone if channel == OtpChannel.SMS.value else User.email
    user = await session.scalar(select(User).where(column == identifier))
    if user is not None:
        return user
    # New people sign up as clients. Contractors are invited (day 3), supervisors are vetted and
    # ops accounts are seeded, so nobody can give themselves another role.
    fields = {"phone": identifier} if channel == OtpChannel.SMS.value else {"email": identifier}
    try:
        async with session.begin_nested():
            user = User(role=Role.CLIENT.value, **fields)
            session.add(user)
    except IntegrityError:
        # Another login created the same account a moment ago.
        user = await session.scalar(select(User).where(column == identifier))
        if user is None:
            raise
    return user


async def verify_otp(
    session: AsyncSession, raw_identifier: str, code: str, *, now: datetime | None = None
) -> TokenPair:
    """Check a code and sign the user in. Commits, including a failed attempt.

    The newest unconsumed code is locked while it is checked, so concurrent attempts are counted one
    by one. After `otp_max_attempts` wrong codes the code is dead, even for the right digits: the
    user must request a new one (which is rate-limited).
    """
    settings = get_settings()
    now = now or _utcnow()
    identifier, channel = normalise_identifier(raw_identifier)
    otp = await session.scalar(
        select(OtpCode)
        .where(OtpCode.identifier == identifier, OtpCode.consumed_at.is_(None))
        .order_by(OtpCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if otp is None:
        raise AppError("invalid_code", "This code is not valid. Request a new one.", 400)
    if otp.attempts >= settings.otp_max_attempts:
        raise AppError("too_many_attempts", "Too many wrong codes. Request a new one.", 429)
    if otp.expires_at <= now:
        raise AppError("otp_expired", "This code has expired. Request a new one.", 400)
    if not hmac.compare_digest(otp.code_hash, _code_hash(settings, identifier, code)):
        otp.attempts += 1
        await session.commit()  # the failed attempt must count even though we return an error
        raise AppError("invalid_code", "This code is not valid.", 400)

    otp.consumed_at = now
    user = await _find_or_create_user(session, identifier, channel)
    if user.status != UserStatus.ACTIVE.value:
        await session.commit()  # the code is used up either way
        raise AppError("account_suspended", "This account is suspended. Contact support.", 403)
    tokens, _ = await _issue_tokens(session, settings, user, now)
    await session.commit()
    return tokens


# --- Tokens ------------------------------------------------------------------------------------


def create_access_token(user: User, *, now: datetime | None = None) -> str:
    settings = get_settings()
    now = now or _utcnow()
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "role": user.role,
        "type": ACCESS_TOKEN_TYPE,
        "iss": JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


async def _issue_tokens(
    session: AsyncSession, settings: Settings, user: User, now: datetime
) -> tuple[TokenPair, RefreshToken]:
    refresh_token = secrets.token_urlsafe(32)
    row = RefreshToken(
        user_id=user.id,
        token_hash=_token_hash(refresh_token),
        expires_at=now + timedelta(days=settings.refresh_token_days),
    )
    session.add(row)
    await session.flush()
    pair = TokenPair(
        access_token=create_access_token(user, now=now),
        refresh_token=refresh_token,
        expires_in=settings.access_token_minutes * 60,
    )
    return pair, row


async def rotate_refresh_token(
    session: AsyncSession, token: str, *, now: datetime | None = None
) -> TokenPair:
    """Exchange a refresh token for a new pair. Commits.

    One conditional UPDATE claims the token, so of two concurrent refreshes only one can succeed.
    Presenting a token that was already exchanged means it may have been copied: every refresh
    token of that user is revoked and they must log in again.
    """
    settings = get_settings()
    now = now or _utcnow()
    token_hash = _token_hash(token)
    claimed = (
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.used_at.is_(None),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .values(used_at=now)
            .returning(RefreshToken.id, RefreshToken.user_id)
        )
    ).one_or_none()

    if claimed is None:
        existing = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if existing is not None and existing.used_at is not None:
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == existing.user_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            await session.commit()
            raise AppError(
                "refresh_token_reused", "This sign-in was ended for your safety. Please log in again.", 401
            )
        raise AppError("invalid_refresh_token", "Your sign-in has expired. Please log in again.", 401)

    token_id, user_id = claimed
    user = await session.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        await session.commit()  # the old token stays used
        raise AppError("account_suspended", "This account is suspended. Contact support.", 403)
    tokens, new_row = await _issue_tokens(session, settings, user, now)
    await session.execute(
        update(RefreshToken).where(RefreshToken.id == token_id).values(replaced_by_id=new_row.id)
    )
    await session.commit()
    return tokens


# --- Who is calling ----------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(401, message, headers={"WWW-Authenticate": "Bearer"})


def decode_access_token(token: str) -> uuid.UUID:
    """Return the user id from a valid access token, or raise 401."""
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Your session has expired. Refresh or log in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Invalid access token.") from exc
    if claims.get("type") != ACCESS_TOKEN_TYPE:
        raise _unauthorized("Invalid access token.")
    try:
        return uuid.UUID(str(claims["sub"]))
    except ValueError as exc:
        raise _unauthorized("Invalid access token.") from exc


async def current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """The signed-in user, read fresh from the database (so role changes and suspensions apply at once)."""
    if credentials is None:
        raise _unauthorized("Sign in first.")
    user = await session.get(User, decode_access_token(credentials.credentials))
    if user is None:
        raise _unauthorized("Invalid access token.")
    if user.status != UserStatus.ACTIVE.value:
        raise AppError("account_suspended", "This account is suspended. Contact support.", 403)
    return user


CurrentUserDep = Annotated[User, Depends(current_user)]


def require_role(*roles: str) -> Callable[[User], Awaitable[User]]:
    """Dependency that lets through only users with one of `roles`; anyone else gets 403."""
    unknown = set(roles) - {r.value for r in Role}
    if not roles or unknown:
        raise ValueError(f"require_role() needs known roles, got {sorted(roles)}")

    async def check(user: CurrentUserDep) -> User:
        if user.role not in roles:
            raise AppError("forbidden_role", "Your role can't do this.", 403)
        return user

    return check


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)
