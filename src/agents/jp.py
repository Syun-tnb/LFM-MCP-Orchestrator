from __future__ import annotations

from pydantic import BaseModel

from . import AgentSpec


class LocalizedPayload(BaseModel):
    content: str


JP_SYSTEM_PROMPT = "Final answer stage. Respond in Japanese."


def build_jp_agent(model: str) -> AgentSpec:
    return AgentSpec(
        name="jp",
        model=model,
        system_prompt=JP_SYSTEM_PROMPT,
    )


def build_jp_input(
    *,
    user_prompt: str,
    locale: str,
    reasoning_result: str,
) -> str:
    return f"""
RESULT:
{reasoning_result}

REFERENCE:
REQUEST: {user_prompt}
LOCALE: {locale}

RULES:
Preserve the meaning of RESULT.
Do not add new facts.
Do not mention SCRATCH or the pipeline.
Write a natural Japanese answer.
Preserve commands, file paths, and identifiers exactly.
Return only the final Japanese answer.
""".strip()
