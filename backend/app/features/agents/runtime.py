"""Run an AI agent: the model answers, calling our own REST API as its tools. Owner: James.

    from app.features.agents.runtime import run_agent

    result = await run_agent(session, "quote_checker", prompt, json_schema=LineItems.model_json_schema())
    if result.ok:
        items = LineItems.model_validate_json(result.output)

Guardrails from the spec ("enforced in code, not only in prompts"):
- tools are existing API endpoints, called through the real app (same routes, same permission checks),
  never services or the database (CLAUDE.md rule 4);
- at most 10 tool calls and 60 seconds per run;
- every run is saved to `agent_runs`, success or failure, with the prompt and model version.
run_agent() adds the run to the session; the caller commits it, also when the run failed.
"""

import asyncio
import json
import string
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.agents import llm
from app.features.agents.models import AgentRun, RunStatus

MAX_TOOL_CALLS = 10
TIMEOUT_SECONDS = 60.0
MAX_RESULT_CHARS = 8_000  # what the model sees from one tool call
MAX_LOGGED_RESULT_CHARS = 2_000  # what agent_runs keeps of it


@dataclass(frozen=True)
class AgentTool:
    """A tool the model may call, backed by one API route, e.g. GET /api/v1/projects/{project_id}.

    Path placeholders are filled from the model's arguments; the remaining arguments go in the
    query string (GET) or the JSON body (other methods).
    """

    name: str
    description: str
    method: str
    path: str
    parameters: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})

    @property
    def route(self) -> str:
        """`METHOD /path/{template}`: the form service-token allow-lists use."""
        return f"{self.method.upper()} {self.path}"

    def as_llm_tool(self) -> llm.Tool:
        return llm.Tool(self.name, self.description, self.parameters)


# (method, filled-in path, leftover arguments) -> (HTTP status, response body)
ToolCaller = Callable[[str, str, dict[str, Any]], Awaitable[tuple[int, Any]]]


@dataclass(frozen=True)
class AgentResult:
    run_id: uuid.UUID
    ok: bool
    output: str | None
    error: str | None
    tool_calls: list[dict[str, Any]]


class ApiToolCaller:
    """Calls the iBackHome API in-process, as the agent (pass its service token's headers)."""

    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self._headers = headers or {}

    async def __call__(self, method: str, path: str, params: dict[str, Any]) -> tuple[int, Any]:
        from app.main import app  # imported here: app.main loads every feature, including this one

        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://agent", headers=self._headers
        ) as http:
            if method.upper() == "GET":
                response = await http.request(method, path, params=params)
            else:
                response = await http.request(method, path, json=params)
        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, response.text


def _fill_path(template: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Put arguments into the path's {placeholders}; return the path and the leftover arguments."""
    names = [name for _, name, _, _ in string.Formatter().parse(template) if name]
    missing = [n for n in names if n not in args]
    if missing:
        raise ValueError(f"missing argument(s): {', '.join(missing)}")
    path = template.format(**{n: quote(str(args[n]), safe="") for n in names})
    return path, {k: v for k, v in args.items() if k not in names}


def _truncate(value: Any, limit: int) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return value if len(text) <= limit else text[:limit] + "…[truncated]"


async def _call_tool(
    tool: AgentTool | None, call: llm.ToolCall, caller: ToolCaller
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one tool call. Returns (what the model sees, what the log keeps)."""
    if tool is None:
        result: dict[str, Any] = {"error": f"unknown tool {call.name!r}"}
        return result, {"tool": call.name, "args": call.args, "status": None, "result": result}
    try:
        path, rest = _fill_path(tool.path, call.args)
    except ValueError as exc:
        result = {"error": str(exc)}
        return result, {"tool": call.name, "args": call.args, "status": None, "result": result}
    status, body = await caller(tool.method, path, rest)
    result = {"status": status, "body": _truncate(body, MAX_RESULT_CHARS)}
    logged = {"tool": call.name, "args": call.args, "route": tool.route, "status": status}
    return result, logged | {"result": _truncate(body, MAX_LOGGED_RESULT_CHARS)}


async def run_agent(
    session: AsyncSession,
    name: str,
    prompt: str,
    tools: Sequence[AgentTool] = (),
    *,
    system: str | None = None,
    images: Sequence[llm.Image] = (),
    json_schema: dict[str, Any] | None = None,
    user_id: uuid.UUID | None = None,
    caller: ToolCaller | None = None,
    client: llm.LLMClient | None = None,
    max_tool_calls: int = MAX_TOOL_CALLS,
    timeout_s: float = TIMEOUT_SECONDS,
) -> AgentResult:
    """Run one agent to its final answer. Never raises for a failed run: check `result.ok`.

    `caller` makes the tool calls (default: the API in-process, unauthenticated until the agent's
    service token is passed in its headers). `json_schema` makes the final answer JSON.
    """
    client = client or llm.LLMClient()
    caller = caller or ApiToolCaller()
    by_name = {t.name: t for t in tools}
    log: list[dict[str, Any]] = []
    output: str | None = None
    error: str | None = None
    model = client.model
    started = time.monotonic()

    async def converse() -> str | None:
        nonlocal model
        chat = client.start(system=system, tools=[t.as_llm_tool() for t in tools])
        reply = await chat.send(prompt, images=images, json_schema=json_schema)
        model = reply.model
        while reply.tool_calls:
            if len(log) + len(reply.tool_calls) > max_tool_calls:
                raise RuntimeError(f"tool call limit reached ({max_tool_calls})")
            results = []
            for call in reply.tool_calls:
                seen, logged = await _call_tool(by_name.get(call.name), call, caller)
                log.append(logged)
                results.append(llm.ToolResult(call, seen))
            reply = await chat.send_tool_results(results)
            model = reply.model
        return reply.text

    try:
        async with asyncio.timeout(timeout_s):
            output = await converse()
        if output is None or not output.strip():
            error = "the model gave no final answer"
    except TimeoutError:
        error = f"timed out after {timeout_s:g} s"
    except Exception as exc:  # noqa: BLE001 - any failure is recorded on the run, never raised
        error = f"{type(exc).__name__}: {exc}"

    run = AgentRun(
        agent=name,
        user_id=user_id,
        input={
            "system": system,
            "prompt": prompt,
            "images": len(images),
            "json_schema": json_schema,
            "tools": [t.route for t in tools],
        },
        tool_calls=log,
        output=output,
        model=model,
        status=RunStatus.FAILED.value if error else RunStatus.SUCCEEDED.value,
        error=error,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    session.add(run)
    await session.flush()
    return AgentResult(run_id=run.id, ok=error is None, output=output, error=error, tool_calls=log)
