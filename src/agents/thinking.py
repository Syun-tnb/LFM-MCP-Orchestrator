from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from . import AgentSpec, RuntimeConstraints


class ThinkingPayload(BaseModel):
    content: str


THINKING_SYSTEM_PROMPT = """
You are lfm-thinking, the reasoning mind of The Trinity.

Convert the user request into a precise execution brief for a local orchestrator.
Stay pragmatic and grounded:
- Prefer the smallest plan that can work on a MacBook Air M4 with 24GB memory.
- Assume models run locally through Ollama and external capabilities arrive through MCP limbs.
- Surface risks, assumptions, and where tools materially improve correctness.
- Transform the request into a compact reasoning brief for the next model.
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
) -> str:
    tool_block = "\n".join(f"- {tool}" for tool in tool_catalog) if tool_catalog else "- No MCP limbs are attached."
    context_block = json.dumps(context, ensure_ascii=True, indent=2, sort_keys=True) if context else "null"
    return f"""
User request:
{user_prompt}

Target locale: {locale}

Runtime constraints:
{constraints.model_dump_json(indent=2)}

Available MCP limbs:
{tool_block}

Additional context:
{context_block}

Produce a practical reasoning brief that makes the next agent faster and safer.
Output only the reasoning itself.
""".strip()
