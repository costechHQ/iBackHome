"""Agent service tokens: each agent may call only the routes on its allow-list. Owner: James.

Spec (AI agents, guardrails): "Agent service tokens carry an allow-list of tools; the API rejects any
other call. No agent token can call approve, release, resolve or pay endpoints."

A service token is a short-lived JWT signed like a login token (same secret, issuer, algorithm) with
"type": "service", the agent's name and its allowed routes as `METHOD /path/{template}` strings.

    token = create_service_token("report", [t.route for t in REPORT_TOOLS], user_id=report_agent.id)
    caller = ApiToolCaller(headers={"Authorization": f"Bearer {token}"})

The sign-in check (Christopher's users.current_user) calls check_route() for service tokens, so a
route that isn't on the list gets 403 route_not_allowed. Money routes are refused twice: when the
token is created and on every request, so no token can ever reach them.
"""

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings
from app.core.errors import AppError

SERVICE_TOKEN_TYPE = "service"  # noqa: S105 - the JWT "type" claim, not a secret
JWT_ALGORITHM = "HS256"  # same as login tokens (users.service)
JWT_ISSUER = "ibackhome"
SERVICE_TOKEN_MINUTES = 10  # one agent run is at most 60 s; a stolen token is useless soon after

# Path words that mean money moves or a decision is made. Matched against every segment of a route.
FORBIDDEN_SEGMENTS = frozenset(
    {
        "approve",
        "fund",
        "funding",
        "pay",
        "payout",
        "payouts",
        "refund",
        "release",
        "releases",
        "resolve",
        "webhooks",
    }
)
# Agents never sign anyone in or mint tokens.
FORBIDDEN_PREFIXES = ("/api/v1/auth",)


def _normalise(route: str) -> tuple[str, str]:
    method, _, path = route.strip().partition(" ")
    return method.upper(), path.strip().rstrip("/") or "/"


def is_forbidden(route: str) -> bool:
    """True for any route no agent may ever call, whatever its allow-list says."""
    _, path = _normalise(route)
    segments = {s.lower() for s in path.split("/") if s}
    return bool(segments & FORBIDDEN_SEGMENTS) or path.startswith(FORBIDDEN_PREFIXES)


def create_service_token(
    agent_name: str,
    allowed_routes: Iterable[str],
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
    minutes: int = SERVICE_TOKEN_MINUTES,
) -> str:
    """A short-lived token for `agent_name`, acting as the agent's user `user_id`.

    Raises ValueError if any route is malformed or forbidden: refusing here means a money route can
    never end up on a token by mistake.
    """
    allowed = sorted({" ".join(_normalise(r)) for r in allowed_routes})
    for route in allowed:
        method, path = _normalise(route)
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"} or not path.startswith("/"):
            raise ValueError(f"not a route: {route!r} (expected 'METHOD /path/{{template}}')")
        if is_forbidden(route):
            raise ValueError(f"agents may never call {route!r}")
    now = now or datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": SERVICE_TOKEN_TYPE,
        "agent": agent_name,
        "allowed": allowed,
        "iss": JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=JWT_ALGORITHM)


def is_service_token(claims: dict[str, Any]) -> bool:
    return claims.get("type") == SERVICE_TOKEN_TYPE


def decode_service_token(token: str) -> dict[str, Any]:
    """The claims of a valid, unexpired service token, or 401 invalid_service_token."""
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        raise AppError("invalid_service_token", "Invalid or expired service token.", 401) from exc
    if not is_service_token(claims) or not isinstance(claims.get("allowed"), list):
        raise AppError("invalid_service_token", "Invalid or expired service token.", 401)
    return claims


def check_route(claims: dict[str, Any], method: str, route_path: str) -> None:
    """Let a service token through only to a route on its list that is never forbidden.

    `route_path` is the matched route's template (FastAPI: request.scope["route"].path), e.g.
    "/api/v1/projects/{project_id}", so ids in the URL don't matter.

    - 403 route_not_allowed
    """
    route = " ".join(_normalise(f"{method} {route_path}"))
    allowed = {" ".join(_normalise(r)) for r in claims.get("allowed", [])}
    if is_forbidden(route) or route not in allowed:
        agent = claims.get("agent", "this agent")
        raise AppError("route_not_allowed", f"The {agent} agent may not call {route}.", 403)
