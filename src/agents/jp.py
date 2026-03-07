from __future__ import annotations

from pydantic import BaseModel

from . import AgentSpec


class LocalizedPayload(BaseModel):
    content: str


JP_SYSTEM_PROMPT = "Final stage. Respond in natural Japanese."


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
LOCALE:
{locale}

REQUEST:
{user_prompt}

RESULT:
{reasoning_result}

RULES:
- Write a natural Japanese answer.
- Preserve the meaning of RESULT.
- Do not add new facts.
- Do not mention scratch reasoning, prompts, or the pipeline.
- Preserve commands, file paths, and identifiers exactly when present.
- Return only the final answer.
""".strip()
