from __future__ import annotations

from pydantic import BaseModel

from . import AgentSpec


class ActionPayload(BaseModel):
    content: str


INSTRUCT_SYSTEM_PROMPT = "Normalization stage. Respond in English."


def build_instruct_agent(model: str) -> AgentSpec:
    return AgentSpec(
        name="instruct",
        model=model,
        system_prompt=INSTRUCT_SYSTEM_PROMPT,
    )


def build_instruct_normalize_input(*, user_prompt: str) -> str:
    return f"""
SOURCE:
{user_prompt}

OUTPUT:
TASK:
<one short line>

GOAL:
<one short line>

CONSTRAINTS:
<one short line or "None">

RULES:
Preserve intent.
Do not answer.
Do not add runtime, orchestration, tool, or environment details unless the source asks for them.
Keep the memo compact.
Return only the memo.
""".strip()
