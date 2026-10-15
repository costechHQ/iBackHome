"""Agent runtime (runtime.py). A fake Gemini stands in for the model; runs are saved (needs Postgres)."""

import asyncio
import secrets
import uuid
from typing import Any

import pytest
from google.genai import types
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.base.users.models import User
from app.features.agents import runtime
from app.features.agents.llm import LLMClient, LLMSettings
from app.features.agents.models import AgentRun

GET_PROJECT = runtime.AgentTool(
    "get_project",
    "Fetch a project",
    "GET",
    "/api/v1/projects/{project_id}",
    {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
)


def text(answer: str) -> dict[str, Any]:
    return {
        "candidates": [{"content": {"role": "model", "parts": [{"text": answer}]}}],
        "model_version": "gem-1",
    }


def call(name: str, **args: Any) -> dict[str, Any]:
    part = {"function_call": {"id": f"c-{secrets.token_hex(3)}", "name": name, "args": args}}
    return {"candidates": [{"content": {"role": "model", "parts": [part]}}], "model_version": "gem-1"}


class FakeModels:
    def __init__(self, replies: list[dict[str, Any]], delay: float = 0) -> None:
        self.replies, self.delay = replies, delay
        self.requests: list[dict[str, Any]] = []

    async def generate_content(self, **request: Any) -> types.GenerateContentResponse:
        self.requests.append({**request, "contents": list(request["contents"])})
        await asyncio.sleep(self.delay)
        return types.GenerateContentResponse.model_validate(self.replies.pop(0))


class FakeGemini:
    def __init__(self, *replies: dict[str, Any], delay: float = 0) -> None:
        self.models = FakeModels(list(replies), delay)
        self.aio = self


def model(*replies: dict[str, Any], delay: float = 0) -> tuple[LLMClient, FakeModels]:
    fake = FakeGemini(*replies, delay=delay)
    return LLMClient(LLMSettings(llm_api_key="unused", llm_model="gem-1"), client=fake), fake.models  # type: ignore[arg-type]


class RecordingCaller:
    def __init__(self, status: int = 200, body: Any = None) -> None:
        self.status, self.body = status, body if body is not None else {"status": "active"}
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def __call__(self, method: str, path: str, params: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((method, path, params))
        return self.status, self.body


async def test_plain_answer_is_saved_with_prompt_and_model(db_session: AsyncSession) -> None:
    client, _ = model(text("All on track."))

    result = await runtime.run_agent(
        db_session, "report", "Summarise the week", system="Be brief.", client=client
    )

    assert (result.ok, result.output, result.error) == (True, "All on track.", None)
    run = await db_session.get(AgentRun, result.run_id)
    assert run is not None
    assert (run.agent, run.status, run.model, run.output) == ("report", "succeeded", "gem-1", "All on track.")
    assert run.input["prompt"] == "Summarise the week" and run.input["system"] == "Be brief."


async def test_tool_call_fills_the_path_and_passes_the_rest_as_query(db_session: AsyncSession) -> None:
    project_id = str(uuid.uuid4())
    client, models = model(call("get_project", project_id=project_id, since="2026-10-12"), text("Active."))
    caller = RecordingCaller()

    result = await runtime.run_agent(
        db_session, "report", "Status?", [GET_PROJECT], client=client, caller=caller
    )

    assert result.ok and result.output == "Active."
    assert caller.calls == [("GET", f"/api/v1/projects/{project_id}", {"since": "2026-10-12"})]
    assert result.tool_calls[0]["route"] == GET_PROJECT.route and result.tool_calls[0]["status"] == 200
    sent_back = models.requests[1]["contents"][-1].parts[0].function_response.response
    assert sent_back == {"status": 200, "body": {"status": "active"}}


async def test_path_values_cannot_escape_into_other_routes(db_session: AsyncSession) -> None:
    client, _ = model(call("get_project", project_id="../../ops/audit"), text("Done."))
    caller = RecordingCaller()

    await runtime.run_agent(db_session, "report", "Status?", [GET_PROJECT], client=client, caller=caller)

    assert caller.calls[0][1] == "/api/v1/projects/..%2F..%2Fops%2Faudit"  # one path segment, not a new route


async def test_unknown_tool_is_reported_to_the_model_not_called(db_session: AsyncSession) -> None:
    client, models = model(call("release_money", milestone_id="m1"), text("I can't do that."))
    caller = RecordingCaller()

    result = await runtime.run_agent(
        db_session, "report", "Pay them", [GET_PROJECT], client=client, caller=caller
    )

    assert result.ok and caller.calls == []
    assert models.requests[1]["contents"][-1].parts[0].function_response.response == {
        "error": "unknown tool 'release_money'"
    }


async def test_missing_path_argument_is_reported_to_the_model(db_session: AsyncSession) -> None:
    client, models = model(call("get_project"), text("Need an id."))
    caller = RecordingCaller()

    await runtime.run_agent(db_session, "report", "Status?", [GET_PROJECT], client=client, caller=caller)

    assert caller.calls == []
    assert (
        "missing argument" in models.requests[1]["contents"][-1].parts[0].function_response.response["error"]
    )


async def test_more_than_ten_tool_calls_fails_the_run(db_session: AsyncSession) -> None:
    replies = [call("get_project", project_id=str(i)) for i in range(11)] + [text("never reached")]
    client, _ = model(*replies)
    caller = RecordingCaller()

    result = await runtime.run_agent(
        db_session, "report", "Loop", [GET_PROJECT], client=client, caller=caller
    )

    assert not result.ok and "tool call limit" in (result.error or "")
    assert len(caller.calls) == runtime.MAX_TOOL_CALLS
    run = await db_session.get(AgentRun, result.run_id)
    assert run is not None and run.status == "failed" and len(run.tool_calls) == 10


async def test_slow_run_times_out_and_is_saved_as_failed(db_session: AsyncSession) -> None:
    client, _ = model(text("too late"), delay=0.5)

    result = await runtime.run_agent(db_session, "report", "Hi", client=client, timeout_s=0.05)

    assert not result.ok and result.error == "timed out after 0.05 s"
    run = await db_session.get(AgentRun, result.run_id)
    assert run is not None and run.status == "failed"


async def test_model_errors_are_recorded_never_raised(db_session: AsyncSession) -> None:
    unconfigured = LLMClient(LLMSettings(llm_api_key=""))

    result = await runtime.run_agent(db_session, "quote_checker", "Extract", client=unconfigured)

    assert not result.ok and "LLM_API_KEY" in (result.error or "")
    run = await db_session.get(AgentRun, result.run_id)
    assert run is not None and run.status == "failed"


async def test_json_answer_for_the_quote_checker(db_session: AsyncSession) -> None:
    schema = {"type": "object", "properties": {"total_minor": {"type": "integer"}}}
    client, models = model(text('{"total_minor": 1800000}'))

    result = await runtime.run_agent(
        db_session, "quote_checker", "Extract", json_schema=schema, client=client
    )

    assert result.output == '{"total_minor": 1800000}'
    assert models.requests[0]["config"].response_json_schema == schema


async def test_tools_go_through_the_real_api_in_process(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role="client", status="active")
    db_session.add(user)
    await db_session.flush()
    get_me = runtime.AgentTool("get_me", "Who am I", "GET", "/api/v1/me")
    llm_client, _ = model(call("get_me"), text("Found you."))
    caller = runtime.ApiToolCaller(headers={"Authorization": f"Bearer {users.create_access_token(user)}"})

    result = await runtime.run_agent(db_session, "report", "Who?", [get_me], client=llm_client, caller=caller)

    assert result.ok
    assert result.tool_calls[0]["status"] == 200
    assert str(user.id) in str(result.tool_calls[0]["result"])


async def test_tool_route_strings_match_service_token_format() -> None:
    assert GET_PROJECT.route == "GET /api/v1/projects/{project_id}"


@pytest.mark.parametrize("bad", [{"a": 1}, "plain text"])
def test_long_results_are_truncated(bad: Any) -> None:
    assert runtime._truncate(bad, 1000) == bad
    assert str(runtime._truncate("x" * 20, 5)).endswith("…[truncated]")
