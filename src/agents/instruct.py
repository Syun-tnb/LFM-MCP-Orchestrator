from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from . import AgentSpec


class ActionPayload(BaseModel):
    content: str


INSTRUCT_SYSTEM_PROMPT = """
You are lfm-instruct, the execution arm of The Trinity.

Turn the reasoning brief into action.
- Use MCP tools only when they improve correctness or fetch required external state.
- Keep tool usage efficient; this system runs on a local MacBook Air.
- Avoid speculative claims when a tool could verify them.
- After you have enough information, respond directly and compactly.
- Transform the reasoning brief into the concrete execution result the final model needs.
- Do NOT repeat the previous agent's input. Only provide your specific action output.
- Output only the core action content with no tags, no JSON, and no preamble.
""".strip()


INSTRUCT_ROUTER_SYSTEM_PROMPT = """
You are lfm-instruct-router, the traffic controller before reasoning.

Inspect the user request and decide how the thinking stage should receive it.
- Keep simple requests simple.
- Request runtime or MCP context only when the user is actually asking about local models, orchestration, tooling, or execution environment.
- Request English normalization only when it materially improves the thinking model's input.
- Do not answer the user request.
- Do not call tools.
- Return JSON only.
""".strip()


def build_instruct_agent(model: str) -> AgentSpec:
    return AgentSpec(
        name="instruct",
        model=model,
        system_prompt=INSTRUCT_SYSTEM_PROMPT,
    )


def build_instruct_router_input(
    *,
    user_prompt: str,
    locale: str,
    context: dict[str, Any] | None = None,
) -> str:
    context_block = json.dumps(context, ensure_ascii=True, indent=2, sort_keys=True) if context else "null"
    return f"""
User request:
{user_prompt}

Target locale: {locale}

Additional context:
{context_block}

Return a JSON object with this shape:
{{
  "thinking_request": "string",
  "include_runtime_context": false,
  "normalize_for_thinking": false,
  "normalize_to_english": false,
  "route_reason": "short string"
}}

Rules:
- Keep "thinking_request" close to the original request unless cleanup is clearly useful.
- Set "include_runtime_context" to true only for runtime/orchestration/tooling/local-LLM requests.
- Set "normalize_for_thinking" to true only when the thinking input should be rewritten before reasoning.
- Set "normalize_to_english" to true only when that rewrite should be in English.
- Keep "route_reason" short and concrete.
""".strip()


def build_instruct_handoff_input(
    *,
    user_prompt: str,
    reasoning_content: str,
    tool_catalog: list[str],
) -> str:
    tool_block = "\n".join(f"- {tool}" for tool in tool_catalog) if tool_catalog else "- No MCP tools are available."
    return f"""
User request:
{user_prompt}

Thinking handoff:
{reasoning_content}

Available tools:
{tool_block}

Do NOT repeat the thinking handoff.
If a tool is useful, call it. When you have enough information, provide only the final action content.
""".strip()


def build_instruct_finalize_input(
    *,
    user_prompt: str,
    reasoning_content: str,
    draft_response: str,
    tool_results: str,
) -> str:
    return f"""
Create the final action block.

User request:
{user_prompt}

Thinking handoff:
{reasoning_content}

Draft response from execution phase:
{draft_response or "(empty)"}

Tool transcript:
{tool_results or "(no tool results)"}

Do NOT repeat the thinking handoff or the tool transcript.
Return only the final action content.
""".strip()
