from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from . import AgentSpec, RuntimeConstraints


class ThinkingPayload(BaseModel):
    request_summary: str
    intent: str
    success_criteria: list[str] = Field(default_factory=list)
    execution_outline: list[str] = Field(default_factory=list)
    tool_strategy: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)
    response_contract: str


THINKING_SYSTEM_PROMPT = """
You are lfm-thinking, the reasoning mind of The Trinity.

Convert the user request into a precise execution brief for a local orchestrator.
Stay pragmatic and grounded:
- Prefer the smallest plan that can work on a MacBook Air M4 with 24GB memory.
- Assume models run locally through Ollama and external capabilities arrive through MCP limbs.
- Surface risks, assumptions, and where tools materially improve correctness.
- Do not write user-facing prose. Produce only the structured execution brief requested by the schema.
""".strip()


def build_thinking_agent(model: str) -> AgentSpec:
    return AgentSpec(
        name="thinking",
        model=model,
        system_prompt=THINKING_SYSTEM_PROMPT,
        response_model=ThinkingPayload,
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

Return a structured execution brief that makes the next agent faster and safer.
""".strip()
