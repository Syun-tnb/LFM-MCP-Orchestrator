from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from typing import Any, TypeVar

import ollama
from pydantic import BaseModel, Field, ValidationError

from agents import (
    ActionPayload,
    LocalizedPayload,
    RuntimeConstraints,
    ThinkingPayload,
    TrinityAgents,
    build_instruct_agent,
    build_instruct_finalize_input,
    build_instruct_handoff_input,
    build_jp_agent,
    build_jp_input,
    build_thinking_agent,
    build_thinking_input,
)
from mcp_runtime import MCPServerConfig, MCPToolRegistry, ToolExecutionRecord

ModelT = TypeVar("ModelT", bound=BaseModel)


class EngineConfig(BaseModel):
    ollama_host: str = Field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"))
    thinking_model: str = Field(default_factory=lambda: os.getenv("LFM_THINKING_MODEL", "lfm-thinking"))
    instruct_model: str = Field(default_factory=lambda: os.getenv("LFM_INSTRUCT_MODEL", "lfm-instruct"))
    jp_model: str = Field(default_factory=lambda: os.getenv("LFM_JP_MODEL", "lfm-jp"))
    target_locale: str = Field(default_factory=lambda: os.getenv("LFM_TARGET_LOCALE", "ja-JP"))
    max_tool_rounds: int = Field(default_factory=lambda: int(os.getenv("LFM_MAX_TOOL_ROUNDS", "4")), ge=1, le=8)
    request_timeout: float = Field(default_factory=lambda: float(os.getenv("LFM_REQUEST_TIMEOUT", "180")), gt=1)
    keep_alive: str | None = Field(default_factory=lambda: os.getenv("OLLAMA_KEEP_ALIVE", "10m"))
    allow_partial_mcp: bool = Field(default_factory=lambda: os.getenv("LFM_ALLOW_PARTIAL_MCP", "true").lower() != "false")
    constraints: RuntimeConstraints = Field(default_factory=RuntimeConstraints)
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)

    @classmethod
    def from_env(
        cls,
        *,
        mcp_servers: list[MCPServerConfig] | None = None,
    ) -> "EngineConfig":
        if mcp_servers is not None:
            return cls(mcp_servers=mcp_servers)

        raw_servers = os.getenv("MCP_SERVERS_JSON", "").strip()
        if not raw_servers:
            return cls()

        parsed = json.loads(raw_servers)
        servers = [MCPServerConfig.model_validate(item) for item in parsed]
        return cls(mcp_servers=servers)


class ModelTrace(BaseModel):
    agent: str
    model: str
    duration_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    stop_reason: str | None = None
    raw_content: str | None = None
    raw_thinking: str | None = None


class OrchestrationResult(BaseModel):
    request: str
    locale: str
    reasoning: ThinkingPayload
    action: ActionPayload
    localized: LocalizedPayload
    tools: list[ToolExecutionRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    traces: list[ModelTrace] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime

    @property
    def final_response(self) -> str:
        return self.localized.final_response


class OrchestratorError(RuntimeError):
    pass


class ModelInvocationError(OrchestratorError):
    pass


class StructuredOutputError(OrchestratorError):
    pass


class OllamaGateway:
    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._client = ollama.AsyncClient(host=config.ollama_host, timeout=config.request_timeout)

    async def chat(
        self,
        *,
        agent_name: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[Any, ModelTrace]:
        started = time.perf_counter()
        try:
            response = await self._client.chat(
                model=model,
                messages=messages,
                tools=tools,
                options=options,
                keep_alive=self._config.keep_alive,
            )
        except Exception as exc:
            raise ModelInvocationError(f"{agent_name} model call failed: {exc}") from exc

        return response, self._build_trace(agent_name=agent_name, model=model, response=response, started=started)

    async def structured_chat(
        self,
        *,
        agent_name: str,
        model: str,
        messages: list[dict[str, Any]],
        response_model: type[ModelT],
        options: dict[str, Any] | None = None,
    ) -> tuple[ModelT, ModelTrace]:
        response, trace = await self.chat(
            agent_name=agent_name,
            model=model,
            messages=messages,
            options=options,
        )
        raw_content = (response.message.content or "").strip()
        payload = _extract_json_payload(raw_content)
        trace.raw_content = raw_content

        try:
            return response_model.model_validate_json(payload), trace
        except ValidationError as exc:
            raise StructuredOutputError(f"{agent_name} returned invalid structured output: {exc}") from exc

    @staticmethod
    def _build_trace(*, agent_name: str, model: str, response: Any, started: float) -> ModelTrace:
        return ModelTrace(
            agent=agent_name,
            model=model,
            duration_ms=int((time.perf_counter() - started) * 1000),
            prompt_tokens=getattr(response, "prompt_eval_count", None),
            completion_tokens=getattr(response, "eval_count", None),
            stop_reason=getattr(response, "done_reason", None),
            raw_content=getattr(response.message, "content", None),
            raw_thinking=getattr(response.message, "thinking", None),
        )


class TrinityOrchestrator:
    def __init__(
        self,
        config: EngineConfig,
        *,
        agents: TrinityAgents | None = None,
        tool_registry: MCPToolRegistry | None = None,
    ) -> None:
        self.config = config
        self.agents = agents or TrinityAgents(
            thinking=build_thinking_agent(config.thinking_model),
            instruct=build_instruct_agent(config.instruct_model),
            jp=build_jp_agent(config.jp_model),
        )
        self.gateway = OllamaGateway(config)
        self.tool_registry = tool_registry or MCPToolRegistry(
            config.mcp_servers,
            allow_partial=config.allow_partial_mcp,
        )
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> "TrinityOrchestrator":
        await self._stack.__aenter__()
        await self._stack.enter_async_context(self.tool_registry)
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> None:
        await self._stack.__aexit__(exc_type, exc, tb)

    async def run(self, user_prompt: str, *, context: dict[str, Any] | None = None) -> OrchestrationResult:
        started_at = datetime.now(UTC)
        warnings = list(self.tool_registry.startup_warnings)
        traces: list[ModelTrace] = []

        tool_catalog = self.tool_registry.render_catalog()
        response, trace = await self.gateway.chat(
            agent_name=self.agents.thinking.name,
            model=self.agents.thinking.model,
            messages=[
                {"role": "system", "content": self.agents.thinking.system_prompt},
                {
                    "role": "user",
                    "content": build_thinking_input(
                        user_prompt=user_prompt,
                        locale=self.config.target_locale,
                        constraints=self.config.constraints,
                        tool_catalog=tool_catalog,
                        context=context,
                    ),
                },
            ],
            options=self.agents.thinking.options,
        )
        raw_reasoning = (response.message.content or "").strip()
        trace.raw_content = raw_reasoning
        reasoning = ThinkingPayload(content=_extract_reasoning_block(raw_reasoning))
        traces.append(trace)

        action, action_traces, tool_records, action_warnings = await self._run_instruct_phase(
            user_prompt=user_prompt,
            reasoning=reasoning,
        )
        traces.extend(action_traces)
        warnings.extend(action_warnings)

        localized, trace = await self.gateway.structured_chat(
            agent_name=self.agents.jp.name,
            model=self.agents.jp.model,
            messages=[
                {"role": "system", "content": self.agents.jp.system_prompt},
                {
                    "role": "user",
                    "content": build_jp_input(
                        user_prompt=user_prompt,
                        locale=self.config.target_locale,
                        reasoning=reasoning,
                        action=action,
                    ),
                },
            ],
            response_model=LocalizedPayload,
            options=self.agents.jp.options,
        )
        traces.append(trace)

        return OrchestrationResult(
            request=user_prompt,
            locale=self.config.target_locale,
            reasoning=reasoning,
            action=action,
            localized=localized,
            tools=tool_records,
            warnings=warnings,
            traces=traces,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )

    async def _run_instruct_phase(
        self,
        *,
        user_prompt: str,
        reasoning: ThinkingPayload,
    ) -> tuple[ActionPayload, list[ModelTrace], list[ToolExecutionRecord], list[str]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.agents.instruct.system_prompt},
            {
                "role": "user",
                "content": build_instruct_handoff_input(
                    user_prompt=user_prompt,
                    reasoning=reasoning,
                    tool_catalog=self.tool_registry.render_catalog(),
                ),
            },
        ]
        traces: list[ModelTrace] = []
        warnings: list[str] = []
        tool_records: list[ToolExecutionRecord] = []
        draft_response = ""
        tools = self.tool_registry.ollama_tools()

        for _ in range(self.config.max_tool_rounds):
            response, trace = await self.gateway.chat(
                agent_name=self.agents.instruct.name,
                model=self.agents.instruct.model,
                messages=messages,
                tools=tools or None,
                options=self.agents.instruct.options,
            )
            traces.append(trace)
            assistant_message = response.message.model_dump(exclude_none=True)
            messages.append(assistant_message)
            draft_response = (response.message.content or "").strip()

            tool_calls = list(getattr(response.message, "tool_calls", None) or [])
            if not tool_calls:
                break

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = dict(tool_call.function.arguments)
                tool_result = await self.tool_registry.call_tool(tool_name, tool_args)
                tool_records.append(tool_result)
                messages.append(tool_result.as_ollama_message())
        else:
            warnings.append("The instruct agent reached the maximum number of tool rounds.")

        action, trace = await self.gateway.structured_chat(
            agent_name=f"{self.agents.instruct.name}-finalize",
            model=self.agents.instruct.model,
            messages=[
                {"role": "system", "content": self.agents.instruct.system_prompt},
                {
                    "role": "user",
                    "content": build_instruct_finalize_input(
                        user_prompt=user_prompt,
                        reasoning=reasoning,
                        draft_response=draft_response,
                        tool_results=[record.model_dump(mode="json") for record in tool_records],
                    ),
                },
            ],
            response_model=ActionPayload,
            options=self.agents.instruct.options,
        )
        traces.append(trace)
        return action, traces, tool_records, warnings


def _extract_json_payload(raw_content: str) -> str:
    text = raw_content.strip()
    if not text:
        raise StructuredOutputError("Model returned an empty response for a structured turn.")

    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "").strip()

    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            candidate = match.group(0)
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                _print_raw_parse_failure(raw_content)
                raise StructuredOutputError(
                    f"Model returned text containing braces, but the extracted JSON was still invalid. Snippet: {_snippet(text)}"
                ) from None

        _print_raw_parse_failure(raw_content)
        raise StructuredOutputError(f"Model did not return valid JSON. No '{{' found. Snippet: {_snippet(text)}")


def _print_raw_parse_failure(raw_content: str) -> None:
    print("Structured output parse failed. Raw model content:", file=sys.stderr)
    print(raw_content, file=sys.stderr)


def _snippet(raw_content: str, *, limit: int = 200) -> str:
    compact = " ".join(raw_content.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


def _extract_reasoning_block(raw_content: str) -> str:
    text = raw_content.strip()
    if not text:
        raise OrchestratorError("Thinking agent returned empty reasoning output.")

    match = re.search(r"<reasoning>(.*?)</reasoning>", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        content = match.group(1).strip()
        if content:
            return content

    # The thinking step is intentionally text-first, so fall back to the raw text
    # if the local model omits the requested tags.
    return text


async def run_orchestrator(
    prompt: str,
    *,
    config: EngineConfig | None = None,
    context: dict[str, Any] | None = None,
) -> OrchestrationResult:
    engine = TrinityOrchestrator(config or EngineConfig.from_env())
    async with engine:
        return await engine.run(prompt, context=context)


def run(prompt: str, *, config: EngineConfig | None = None, context: dict[str, Any] | None = None) -> OrchestrationResult:
    return asyncio.run(run_orchestrator(prompt, config=config, context=context))
