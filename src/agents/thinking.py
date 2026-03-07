from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from . import AgentSpec, RuntimeConstraints


class ThinkingPayload(BaseModel):
    content: str


THINKING_SYSTEM_PROMPT = """
You are lfm-thinking, the reasoning mind of The Trinity.

Convert the user request into a compact reasoning brief for the next stage.
- Keep the brief proportional to the request.
- Surface assumptions, risks, and whether tools are actually needed.
- Use runtime or tool context only when it is relevant to the request.
- Do not write user-facing prose.
- Do NOT repeat the user's input. Only provide your specific reasoning output.
- Output only the core reasoning content with no tags, no JSON, and no preamble.
""".strip()


def build_thinking_agent(model: str) -> AgentSpec:
    return AgentSpec(
        name="thinking",
        model=model,
        system_prompt=THINKING_SYSTEM_PROMPT,
    )


def build_thinking_input(
    *,
    user_prompt: str,
    locale: str,
    constraints: RuntimeConstraints,
    tool_catalog: list[str],
    context: dict[str, Any] | None = None,
    route_reason: str | None = None,
    include_runtime_context: bool = False,
) -> str:
    sections = [f"Reasoning request:\n{user_prompt.strip()}"]

    if route_reason and include_runtime_context:
        sections.append(f"Router note:\n{route_reason.strip()}")

    if context:
        sections.append(f"Additional context:\n{_render_context_block(context)}")

    if include_runtime_context:
        sections.append(
            _build_runtime_context_block(
                locale=locale,
                constraints=constraints,
                tool_catalog=tool_catalog,
            )
        )

    sections.append("Write a short reasoning brief for the next stage.")
    return "\n\n".join(section for section in sections if section).strip()


def _build_runtime_context_block(
    *,
    locale: str,
    constraints: RuntimeConstraints,
    tool_catalog: list[str],
) -> str:
    sections = []

    if locale:
        sections.append(f"Target locale: {locale}")

    sections.append(f"Runtime context:\n{constraints.model_dump_json(indent=2)}")

    if tool_catalog:
        tool_block = "\n".join(f"- {tool}" for tool in tool_catalog)
        sections.append(f"Available MCP tools:\n{tool_block}")

    return "\n\n".join(sections)


def _render_context_block(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=True, indent=2, sort_keys=True)
