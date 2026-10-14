"""JSON logs with a request ID (API and Celery), and Sentry settings."""

import json
import logging
from types import SimpleNamespace
from typing import Any

import pytest
import sentry_sdk
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from app.core import observability
from app.core.config import Settings
from app.main import create_app


def _json_line(record: logging.LogRecord) -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads(observability.JsonFormatter().format(record))
    return parsed


# --- request IDs -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sent", "kept"),
    [
        ("3f2a9c1e-7b1d-4e0a-9f00-2b8c1d0e5a11", True),
        ("abc.DEF_123-xyz", True),
        ("short", False),  # under 8 characters
        ("x" * 65, False),
        ("bad id with spaces", False),
        ('"},{"injected":1', False),  # never let a header shape the JSON log line
        (None, False),
    ],
)
def test_accept_request_id(sent: str | None, kept: bool) -> None:
    result = observability.accept_request_id(sent)
    assert (result == sent) is kept
    assert 8 <= len(result) <= 64


async def test_every_response_has_a_request_id(client: AsyncClient) -> None:
    first = await client.get("/healthz")
    second = await client.get("/healthz")
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]
    assert len(first.headers["X-Request-ID"]) == 32


async def test_a_safe_incoming_request_id_is_kept(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me", headers={"X-Request-ID": "support-case-12345"})
    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == "support-case-12345"


async def test_one_log_line_per_request_with_the_id(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = await client.get("/api/v1/me", headers={"X-Request-ID": "trace-me-0001"})
    [record] = [r for r in caplog.records if r.name == "app.request"]
    line = _json_line(record)
    assert line["request_id"] == "trace-me-0001" == response.headers["X-Request-ID"]
    assert (line["method"], line["path"], line["status"]) == ("GET", "/api/v1/me", 401)
    assert line["message"] == "GET /api/v1/me 401"
    assert isinstance(line["duration_ms"], float)


async def test_a_500_carries_the_request_id_and_logs_it(caplog: pytest.LogCaptureFixture) -> None:
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    app = create_app()  # replaces the root handlers with the JSON one; put pytest's capture back
    root.handlers, root.level = saved[0], saved[1]
    boom = APIRouter()

    @boom.get("/boom")
    async def explode() -> None:
        raise RuntimeError("database fell over")

    app.include_router(boom)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    with caplog.at_level(logging.INFO):
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            response = await http.get("/boom", headers={"X-Request-ID": "incident-0042"})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.headers["X-Request-ID"] == "incident-0042"
    assert "database fell over" not in response.text  # details stay in the logs
    error = next(r for r in caplog.records if r.levelno == logging.ERROR)
    line = _json_line(error)
    assert line["request_id"] == "incident-0042"
    assert "RuntimeError: database fell over" in line["exception"]
    access = next(r for r in caplog.records if r.name == "app.request")
    assert _json_line(access)["status"] == 500


# --- the JSON format -----------------------------------------------------------------------------------


def test_json_line_has_the_fields_and_extras() -> None:
    token = observability.request_id_var.set("req-00000001")
    try:
        record = logging.LogRecord("app.test", logging.WARNING, __file__, 1, "claimed %s", ("m1",), None)
        record.milestone_id = "m1"
        line = _json_line(record)
    finally:
        observability.request_id_var.reset(token)
    assert line["level"] == "WARNING"
    assert line["logger"] == "app.test"
    assert line["message"] == "claimed m1"
    assert line["request_id"] == "req-00000001"
    assert line["milestone_id"] == "m1"
    assert line["ts"].endswith("Z")


def test_configure_logging_writes_json_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    try:
        observability.configure_logging(Settings(log_level="info"))
        logging.getLogger("app.test").info("hello", extra={"project_id": "p1"})
        line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert (line["message"], line["project_id"], line["level"]) == ("hello", "p1", "INFO")
        assert logging.getLogger("uvicorn.access").disabled
    finally:
        root.handlers, root.level = saved[0], saved[1]


# --- Celery ------------------------------------------------------------------------------------------


def test_queued_task_carries_the_request_id() -> None:
    token = observability.request_id_var.set("req-from-api-1")
    try:
        headers: dict[str, Any] = {}
        observability.add_request_id_to_task(headers=headers, body=None)
        assert headers["request_id"] == "req-from-api-1"
    finally:
        observability.request_id_var.reset(token)


def test_no_request_no_header() -> None:
    token = observability.request_id_var.set(None)
    try:
        headers: dict[str, Any] = {}
        observability.add_request_id_to_task(headers=headers)
        assert headers == {}
    finally:
        observability.request_id_var.reset(token)


def test_task_logs_under_the_request_id_that_queued_it() -> None:
    token = observability.request_id_var.set(None)
    try:
        observability.restore_request_id_in_task(
            task=SimpleNamespace(request=SimpleNamespace(request_id="req-from-api-1"))
        )
        assert observability.current_request_id() == "req-from-api-1"
        # A scheduled (Beat) task has no request: it gets a fresh ID.
        observability.restore_request_id_in_task(task=SimpleNamespace(request=SimpleNamespace()))
        fresh = observability.current_request_id()
        assert fresh and fresh != "req-from-api-1"
    finally:
        observability.request_id_var.reset(token)


def test_celery_signals_are_connected() -> None:
    from celery.signals import before_task_publish, setup_logging, task_prerun, worker_init

    import app.workers.celery_app as worker

    receivers = {
        "publish": before_task_publish.receivers,
        "prerun": task_prerun.receivers,
        "logging": setup_logging.receivers,
        "init": worker_init.receivers,
    }
    connected = {name: [r[1] for r in found] for name, found in receivers.items()}
    assert observability.add_request_id_to_task in connected["publish"]
    assert observability.restore_request_id_in_task in connected["prerun"]
    assert worker._json_logs in connected["logging"]
    assert worker._error_tracking in connected["init"]


# --- Sentry ----------------------------------------------------------------------------------------


def test_sentry_is_off_without_a_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: calls.append(kw))
    assert observability.init_sentry(Settings(sentry_dsn=""), "api") is False
    assert calls == []


def test_sentry_never_sends_bodies_or_personal_data(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    tags: dict[str, str] = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: calls.append(kw))
    monkeypatch.setattr(sentry_sdk, "set_tag", lambda k, v: tags.__setitem__(k, v))
    settings = Settings(sentry_dsn="https://key@o1.ingest.sentry.io/1", environment="local")
    assert observability.init_sentry(settings, "worker") is True
    [kwargs] = calls
    assert kwargs["dsn"] == "https://key@o1.ingest.sentry.io/1"
    assert kwargs["send_default_pii"] is False
    assert kwargs["max_request_body_size"] == "never"  # an OTP code in a body must never leave us
    assert kwargs["environment"] == "local"
    assert tags == {"component": "worker"}
