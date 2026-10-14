"""Structured JSON logs with a request ID, and error tracking (Sentry). Owner: Christopher.

Every log line is one JSON object on stdout:

    {"ts": "2026-10-14T09:30:01.123Z", "level": "INFO", "logger": "app.request",
     "message": "GET /api/v1/projects 200", "request_id": "3f2a...", "method": "GET", ...}

The request ID comes from the caller's `X-Request-ID` header (if it looks safe) or is generated,
is returned in the response's `X-Request-ID` header, is attached to every log line written while
the request runs, and travels with any Celery task the request queues (and on into that task's
logs). Support can ask a user for it and find everything that happened.

Use the standard library anywhere; extra fields go in `extra`:

    logger = logging.getLogger(__name__)
    logger.info("milestone claimed", extra={"milestone_id": str(milestone.id)})

Never log secrets (OTP codes, tokens, keys) or full request bodies.
"""

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

import sentry_sdk
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# LogRecord attributes that are not "extra" fields.
_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}


def current_request_id() -> str | None:
    return request_id_var.get()


def new_request_id() -> str:
    return uuid.uuid4().hex


def accept_request_id(value: str | None) -> str:
    """The caller's ID if it is 8-64 safe characters (it ends up in logs), else a new one."""
    if value and _SAFE_REQUEST_ID.fullmatch(value):
        return value
    return new_request_id()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        at = datetime.fromtimestamp(record.created, UTC)
        entry: dict[str, Any] = {
            "ts": at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or current_request_id(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in entry:
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(settings: Settings) -> None:
    """Send every log line (ours, uvicorn's, Celery's) to stdout as JSON. Safe to call twice."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())
    # Our middleware writes one line per request with the request ID; uvicorn's own access line would
    # be a second, ID-less copy.
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False
    access.disabled = True


class RequestIdMiddleware:
    """Gives every HTTP request an ID, returns it in X-Request-ID, and logs one line per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger("app.request")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        request_id = accept_request_id(headers.get(REQUEST_ID_HEADER.lower()))
        # Not reset afterwards on purpose: the 500 handler runs outside this middleware and still
        # needs the ID. Each request runs in its own task, so it never leaks into another request.
        request_id_var.set(request_id)
        sentry_sdk.set_tag("request_id", request_id)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", [])
                message["headers"] = [
                    *message["headers"],
                    (REQUEST_ID_HEADER.encode("latin-1"), request_id.encode("latin-1")),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            self.logger.info(
                "%s %s %s",
                scope["method"],
                scope["path"],
                status,
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )


def init_sentry(settings: Settings, component: str) -> bool:
    """Turn on error tracking when SENTRY_DSN is set. `component` is "api" or "worker".

    The FastAPI, Starlette and Celery integrations switch on by themselves. Request bodies and
    personal data are never sent: an OTP code or token must never leave our servers.
    """
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        max_request_body_size="never",
    )
    sentry_sdk.set_tag("component", component)
    return True


# --- Celery: the request ID travels with the task ----------------------------------------------------

TASK_HEADER = "request_id"


def add_request_id_to_task(headers: dict[str, Any] | None = None, **_: Any) -> None:
    """before_task_publish: put the current request ID in the task message's headers."""
    request_id = current_request_id()
    if headers is not None and request_id:
        headers.setdefault(TASK_HEADER, request_id)


def restore_request_id_in_task(task: Any = None, **_: Any) -> None:
    """task_prerun: log the task under the request ID that queued it (or a new one, e.g. for Beat)."""
    sent = getattr(getattr(task, "request", None), TASK_HEADER, None)
    request_id = accept_request_id(sent if isinstance(sent, str) else None)
    request_id_var.set(request_id)
    sentry_sdk.set_tag("request_id", request_id)
