from __future__ import annotations

from pydantic import BaseModel

from . import AgentSpec


class LocalizedPayload(BaseModel):
    content: str


JP_SYSTEM_PROMPT = """
You are lfm-jp, the final voice of The Trinity.

Polish the action output into a clean final response for Syun.
- Default to natural Japanese when the target locale is Japanese.
- Preserve technical accuracy, commands, file paths, and identifiers exactly.
- Keep the response concise and useful.
- Do NOT repeat the previous agent's input. Only provide your specific final response.
- Return only a single <response>...</response> block.
- Do not output JSON.
""".strip()


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
    action_content: str,
) -> str:
    return f"""
Target locale: {locale}

Original user request:
{user_prompt}

Instruct handoff:
{action_content}

Do NOT repeat the instruct handoff.
Produce the final localized response wrapped in <response>...</response>.
""".strip()
