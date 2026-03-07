from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from . import AgentSpec, RuntimeConstraints


class ThinkingPayload(BaseModel):
    content: str


THINKING_SYSTEM_PROMPT = """
You are lfm-thinking, the reasoning mind of The Trinity.

Convert the user request into a compact reasoning brief for the next stage.
- Keep the brief proportional to the request.
- Surface assumptions, risks, and whether tools are actually needed.
- Use runtime or tool context only when it is relevant to the request.
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
    sections = [f"User request:\n{user_prompt.strip()}"]

    if _should_include_locale_context(user_prompt, locale):
        sections.append(f"Target locale: {locale}")

    optional_context = _build_optional_thinking_context(
        user_prompt=user_prompt,
        constraints=constraints,
        tool_catalog=tool_catalog,
        context=context,
    )
    if optional_context:
        sections.append(optional_context)

    sections.append("Write a short reasoning brief for the next stage.")
    return "\n\n".join(section for section in sections if section).strip()


def _build_optional_thinking_context(
    *,
    user_prompt: str,
    constraints: RuntimeConstraints,
    tool_catalog: list[str],
    context: dict[str, Any] | None,
) -> str:
    sections: list[str] = []

    if context:
        sections.append(
            "Additional context:\n"
            f"{json.dumps(context, ensure_ascii=True, indent=2, sort_keys=True)}"
        )

    if _should_include_runtime_context(user_prompt):
        sections.append(f"Runtime constraints:\n{constraints.model_dump_json(indent=2)}")
        if tool_catalog:
            tool_block = "\n".join(f"- {tool}" for tool in tool_catalog)
            sections.append(f"Available MCP tools:\n{tool_block}")

    return "\n\n".join(sections).strip()


def _should_include_runtime_context(user_prompt: str) -> bool:
    prompt = user_prompt.casefold()
    keywords = (
        "agent",
        "cli",
        "local model",
        "local llm",
        "mcp",
        "model",
        "ollama",
        "orchestr",
        "prompt",
        "python",
        "runtime",
        "tool",
        "uv",
        "workflow",
        "モデル",
        "エージェント",
        "オーケスト",
        "ツール",
        "ランタイム",
        "ローカル",
    )
    return any(keyword in prompt for keyword in keywords)


def _should_include_locale_context(user_prompt: str, locale: str) -> bool:
    if not locale:
        return False

    prompt = user_prompt.casefold()
    locale_keywords = (
        "english",
        "japanese",
        "language",
        "locale",
        "translate",
        "translation",
        "日本語",
        "英語",
        "翻訳",
        "言語",
    )
    return any(keyword in prompt for keyword in locale_keywords)
