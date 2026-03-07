from __future__ import annotations

import json

from pydantic import BaseModel, Field

from . import AgentSpec
from .thinking import ThinkingPayload


class ActionPayload(BaseModel):
    execution_summary: str
    final_answer_draft: str
    completed_steps: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    error_notes: list[str] = Field(default_factory=list)


INSTRUCT_SYSTEM_PROMPT = """
You are lfm-instruct, the execution arm of The Trinity.

Turn the reasoning brief into action.
- Use MCP tools only when they improve correctness or fetch required external state.
- Keep tool usage efficient; this system runs on a local MacBook Air.
- Avoid speculative claims when a tool could verify them.
- After you have enough information, respond directly and compactly.
""".strip()


def build_instruct_agent(model: str) -> AgentSpec:
    return AgentSpec(
        name="instruct",
        model=model,
        system_prompt=INSTRUCT_SYSTEM_PROMPT,
        response_model=ActionPayload,
    )


def build_instruct_handoff_input(
    *,
    user_prompt: str,
    reasoning: ThinkingPayload,
    tool_catalog: list[str],
) -> str:
    tool_block = "\n".join(f"- {tool}" for tool in tool_catalog) if tool_catalog else "- No MCP tools are available."
    return f"""
User request:
{user_prompt}

Reasoning brief:
<reasoning>
{reasoning.content}
</reasoning>

Available tools:
{tool_block}

If a tool is useful, call it. When you have enough information, provide a direct draft answer.
""".strip()


def build_instruct_finalize_input(
    *,
    user_prompt: str,
    reasoning: ThinkingPayload,
    draft_response: str,
    tool_results: list[dict[str, object]],
) -> str:
    tool_block = json.dumps(tool_results, ensure_ascii=True, indent=2, sort_keys=True) if tool_results else "[]"
    return f"""
Create the final structured action payload.

User request:
{user_prompt}

Reasoning brief:
<reasoning>
{reasoning.content}
</reasoning>

Draft response from execution phase:
{draft_response or "(empty)"}

Tool results:
{tool_block}

Return only the structured payload requested by the schema.
""".strip()
