"""Thin wrapper over the LLM API (Google Gemini). Owner: James.

Everything outside this file talks in the plain types below (Tool, ToolCall, ToolResult, Image),
so switching provider later means rewriting this one file.

One-shot (e.g. the quote checker, with a JSON schema for the answer):

    reply = await LLMClient().generate("Extract the line items", json_schema=LineItems.model_json_schema())

With tools (the agent runtime loops like this, capped at 10 calls):

    chat = LLMClient().start(system="You write weekly reports.", tools=[get_project_tool])
    reply = await chat.send("Write this week's report for project 42")
    while reply.tool_calls:
        reply = await chat.send_tool_results([ToolResult(call, call_api(call)) for call in reply.tool_calls])

Settings come from the environment: LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT_SECONDS.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import AppError

# Retry rate limits and brief outages; the free tier returns 429 when its quota is used up.
_RETRY_STATUS_CODES = [408, 429, 500, 502, 503, 504]


class LLMSettings(BaseSettings):
    # Also reads the repo-root .env, so running from backend/ outside Docker finds the key.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    llm_api_key: str = ""
    # A pinned version, not "-latest", so a stored agent run can be reproduced (spec: AI agents).
    # Flash-lite: the free tier allows only 5 requests a minute on gemini-3.8-flash, and one report
    # run can make 11. Matches .env.example; LLM_MODEL still overrides it.
    llm_model: str = "gemini-3.5-flash-lite"
    llm_timeout_seconds: float = 60
    llm_retry_attempts: int = 4


@dataclass(frozen=True)
class Tool:
    """A function the model may call. `parameters` is a JSON schema for its arguments."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any]
    id: str | None = None


@dataclass(frozen=True)
class ToolResult:
    call: ToolCall
    result: dict[str, Any]


@dataclass(frozen=True)
class Image:
    data: bytes
    mime_type: str = "image/jpeg"


@dataclass(frozen=True)
class LLMReply:
    text: str | None
    tool_calls: list[ToolCall]
    model: str
    input_tokens: int
    output_tokens: int


class LLMClient:
    def __init__(self, settings: LLMSettings | None = None, client: genai.Client | None = None) -> None:
        self.settings = settings or LLMSettings()
        self._client = client

    @property
    def model(self) -> str:
        return self.settings.llm_model

    def _api(self) -> genai.Client:
        if self._client is None:
            if not self.settings.llm_api_key:
                raise AppError("llm_not_configured", "LLM_API_KEY is not set.", 503)
            self._client = genai.Client(
                api_key=self.settings.llm_api_key,
                http_options=types.HttpOptions(
                    timeout=int(self.settings.llm_timeout_seconds * 1000),
                    retry_options=types.HttpRetryOptions(
                        attempts=self.settings.llm_retry_attempts, http_status_codes=_RETRY_STATUS_CODES
                    ),
                ),
            )
        return self._client

    def start(self, system: str | None = None, tools: Sequence[Tool] = ()) -> "Chat":
        return Chat(self, system, tools)

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        images: Sequence[Image] = (),
        json_schema: dict[str, Any] | None = None,
    ) -> LLMReply:
        """One prompt, one answer. With `json_schema`, the answer text is JSON matching it."""
        return await self.start(system).send(prompt, images=images, json_schema=json_schema)


class Chat:
    """One conversation. Keeps the model's own turns verbatim, which Gemini needs for tool calls."""

    def __init__(self, llm: LLMClient, system: str | None, tools: Sequence[Tool]) -> None:
        self._llm = llm
        self._system = system
        declarations = [
            types.FunctionDeclaration(
                name=t.name, description=t.description, parameters_json_schema=t.parameters
            )
            for t in tools
        ]
        self._tools: list[types.ToolUnion] | None = (
            [types.Tool(function_declarations=declarations)] if declarations else None
        )
        self.history: list[types.ContentUnion] = []

    async def send(
        self, prompt: str, *, images: Sequence[Image] = (), json_schema: dict[str, Any] | None = None
    ) -> LLMReply:
        parts = [types.Part.from_bytes(data=i.data, mime_type=i.mime_type) for i in images]
        parts.append(types.Part.from_text(text=prompt))
        return await self._turn(types.Content(role="user", parts=parts), json_schema)

    async def send_tool_results(self, results: Sequence[ToolResult]) -> LLMReply:
        parts = [types.Part.from_function_response(name=r.call.name, response=r.result) for r in results]
        for part, r in zip(parts, results, strict=True):
            if part.function_response is not None:
                part.function_response.id = r.call.id
        return await self._turn(types.Content(role="user", parts=parts), None)

    async def _turn(self, content: types.Content, json_schema: dict[str, Any] | None) -> LLMReply:
        self.history.append(content)
        config = types.GenerateContentConfig(
            system_instruction=self._system,
            tools=self._tools,
            # We run the tools ourselves (through the API, with the agent's token), never the SDK.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            response_mime_type="application/json" if json_schema else None,
            response_json_schema=json_schema,
        )
        response = await self._llm._api().aio.models.generate_content(
            model=self._llm.model, contents=self.history, config=config
        )
        candidate = response.candidates[0] if response.candidates else None
        if candidate is None or candidate.content is None:
            raise AppError("llm_empty_reply", "The language model returned no answer.", 502)
        self.history.append(candidate.content)

        # Read the parts ourselves: response.text warns whenever the reply also holds tool calls.
        parts = candidate.content.parts or []
        texts = [p.text for p in parts if p.text and not p.thought]
        usage = response.usage_metadata
        return LLMReply(
            text="".join(texts) if texts else None,
            tool_calls=[
                ToolCall(
                    name=p.function_call.name or "",
                    args=dict(p.function_call.args or {}),
                    id=p.function_call.id,
                )
                for p in parts
                if p.function_call
            ],
            model=response.model_version or self._llm.model,
            input_tokens=(usage.prompt_token_count or 0) if usage else 0,
            output_tokens=(usage.candidates_token_count or 0) if usage else 0,
        )
