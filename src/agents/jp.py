from __future__ import annotations

from pydantic import BaseModel, Field

from . import AgentSpec
from .instruct import ActionPayload
from .thinking import ThinkingPayload


class LocalizedPayload(BaseModel):
    locale: str
    final_response: str
    summary: str
    follow_up: list[str] = Field(default_factory=list)


JP_SYSTEM_PROMPT = """
You are lfm-jp, the final voice of The Trinity.

Polish the action output into a clean final response for Syun.
- Default to natural Japanese when the target locale is Japanese.
- Preserve technical accuracy, commands, file paths, and identifiers exactly.
- Keep the response concise and useful.
- Return only the structured payload requested by the schema.
""".strip()


def build_jp_agent(model: str) -> AgentSpec:
    return AgentSpec(
        name="jp",
        model=model,
        system_prompt=JP_SYSTEM_PROMPT,
        response_model=LocalizedPayload,
    )


def build_jp_input(
    *,
    user_prompt: str,
    locale: str,
    reasoning: ThinkingPayload,
    action: ActionPayload,
) -> str:
    return f"""
Target locale: {locale}

Original user request:
{user_prompt}

Reasoning brief:
{reasoning.model_dump_json(indent=2)}

Action payload:
{action.model_dump_json(indent=2)}

Produce the final localized response.
""".strip()
