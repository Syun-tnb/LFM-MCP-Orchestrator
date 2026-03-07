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

TASK:
Convert the source into a compact English task memo for the reasoning stage.

FORMAT:
TASK:
<one short line>

GOAL:
<one short line>

CONSTRAINTS:
<one short line or "None">

RULES:
- Preserve the user's intent.
- Do not answer the request.
- Do not add runtime, orchestration, tool, or environment details unless the source asks about them.
- Keep the memo compact and literal.
- Return only the memo.
""".strip()
