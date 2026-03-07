from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from . import AgentSpec, RuntimeConstraints


class ThinkingPayload(BaseModel):
    content: str


THINKING_SYSTEM_PROMPT = "Reasoning stage. Respond in English."


def build_thinking_agent(model: str) -> AgentSpec:
    return AgentSpec(
        name="thinking",
        model=model,
        system_prompt=THINKING_SYSTEM_PROMPT,
    )


def build_thinking_input(
    *,
    task_memo: str,
    constraints: RuntimeConstraints,
    context: dict[str, Any] | None = None,
    include_runtime_context: bool = False,
) -> str:
    sections = [f"TASK_MEMO:\n{task_memo.strip()}"]

    if include_runtime_context:
        sections.append(
            _build_runtime_context_block(
                constraints=constraints,
            )
        )

    if context:
        sections.append(f"CONTEXT:\n{_render_context_block(context)}")

    sections.append(
        "\n".join(
            [
                "OUTPUT:",
                "Return exactly this format.",
                "SCRATCH:",
                "<short internal reasoning>",
                "",
                "RESULT:",
                "<one concise English conclusion>",
            ]
        )
    )
    return "\n\n".join(section for section in sections if section).strip()


def _build_runtime_context_block(
    *,
    constraints: RuntimeConstraints,
) -> str:
    return f"RUNTIME:\n{constraints.model_dump_json(indent=2)}"


def _render_context_block(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=True, indent=2, sort_keys=True)
