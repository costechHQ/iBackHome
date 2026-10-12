"""Tests for llm.py. A fake Gemini client stands in for the real API, so no key or network is needed."""

from typing import Any

import pytest
from google.genai import types

from app.core.errors import AppError
from app.features.agents.llm import Image, LLMClient, LLMSettings, Tool, ToolCall, ToolResult


class FakeModels:
    def __init__(self, replies: list[dict[str, Any]]) -> None:
        self.replies = replies
        self.requests: list[dict[str, Any]] = []

    async def generate_content(self, **request: Any) -> types.GenerateContentResponse:
        # Copy the history: the chat keeps appending to the same list after this call.
        self.requests.append({**request, "contents": list(request["contents"])})
        return types.GenerateContentResponse.model_validate(self.replies.pop(0))


class FakeClient:
    def __init__(self, *replies: dict[str, Any]) -> None:
        self.models = FakeModels(list(replies))
        self.aio = self


def reply(*parts: dict[str, Any], prompt_tokens: int = 12, answer_tokens: int = 5) -> dict[str, Any]:
    return {
        "candidates": [{"content": {"role": "model", "parts": list(parts)}}],
        "usage_metadata": {"prompt_token_count": prompt_tokens, "candidates_token_count": answer_tokens},
        "model_version": "gemini-test",
    }


def client_with(*replies: dict[str, Any], model: str = "gemini-test") -> tuple[LLMClient, FakeModels]:
    fake = FakeClient(*replies)
    return LLMClient(LLMSettings(llm_api_key="unused", llm_model=model), client=fake), fake.models  # type: ignore[arg-type]


async def test_generate_returns_text_and_token_counts() -> None:
    llm, models = client_with(reply({"text": "Two milestones done."}))

    answer = await llm.generate("Summarise", system="Be brief.")

    assert answer.text == "Two milestones done."
    assert answer.tool_calls == []
    assert (answer.input_tokens, answer.output_tokens) == (12, 5)
    request = models.requests[0]
    assert request["model"] == "gemini-test"
    assert request["config"].system_instruction == "Be brief."
    assert request["config"].automatic_function_calling.disable is True


async def test_model_name_comes_from_settings() -> None:
    llm, models = client_with(reply({"text": "ok"}), model="gemini-2.5-pro")

    await llm.generate("hi")

    assert models.requests[0]["model"] == "gemini-2.5-pro"


async def test_images_are_sent_before_the_prompt() -> None:
    llm, models = client_with(reply({"text": "A block wall at lintel level."}))

    await llm.generate("What stage is this?", images=[Image(b"\xff\xd8jpeg-bytes")])

    parts = models.requests[0]["contents"][0].parts
    assert parts[0].inline_data.data == b"\xff\xd8jpeg-bytes"
    assert parts[0].inline_data.mime_type == "image/jpeg"
    assert parts[1].text == "What stage is this?"


async def test_json_schema_asks_for_json() -> None:
    schema = {"type": "object", "properties": {"total_minor": {"type": "integer"}}}
    llm, models = client_with(reply({"text": '{"total_minor": 500000}'}))

    answer = await llm.generate("Extract the total", json_schema=schema)

    assert answer.text == '{"total_minor": 500000}'
    config = models.requests[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == schema


async def test_tool_call_round_trip_keeps_history() -> None:
    get_project = Tool(
        "get_project",
        "Fetch a project by id",
        {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
    )
    llm, models = client_with(
        reply({"function_call": {"id": "call-1", "name": "get_project", "args": {"project_id": "p1"}}}),
        reply({"text": "Project p1 is active."}),
    )
    chat = llm.start(system="You write reports.", tools=[get_project])

    first = await chat.send("How is p1 doing?")
    assert first.tool_calls == [ToolCall(name="get_project", args={"project_id": "p1"}, id="call-1")]

    second = await chat.send_tool_results([ToolResult(first.tool_calls[0], {"status": "active"})])
    assert second.text == "Project p1 is active."

    declared = models.requests[0]["config"].tools[0].function_declarations[0]
    assert declared.name == "get_project"
    assert declared.parameters_json_schema == get_project.parameters

    # Second request = user prompt, the model's own tool-call turn verbatim, then our tool result.
    user, model_turn, tool_turn = models.requests[1]["contents"]
    assert user.parts[0].text == "How is p1 doing?"
    assert model_turn.role == "model"
    assert model_turn.parts[0].function_call.name == "get_project"
    response = tool_turn.parts[0].function_response
    assert (response.name, response.id, response.response) == ("get_project", "call-1", {"status": "active"})
    assert len(chat.history) == 4


async def test_empty_reply_is_an_error() -> None:
    llm, _ = client_with({"candidates": []})

    with pytest.raises(AppError) as error:
        await llm.generate("hi")

    assert error.value.code == "llm_empty_reply"


async def test_missing_api_key_is_a_clear_error() -> None:
    llm = LLMClient(LLMSettings(llm_api_key=""))

    with pytest.raises(AppError) as error:
        await llm.generate("hi")

    assert (error.value.code, error.value.status_code) == ("llm_not_configured", 503)
