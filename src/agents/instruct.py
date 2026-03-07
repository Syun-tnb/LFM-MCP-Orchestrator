from __future__ import annotations

from pydantic import BaseModel

from . import AgentSpec


class ActionPayload(BaseModel):
    content: str


INSTRUCT_SYSTEM_PROMPT = """
You are lfm-instruct, the execution arm of The Trinity.

Turn the reasoning brief into action.
- Use MCP tools only when they improve correctness or fetch required external state.
- Keep tool usage efficient; this system runs on a local MacBook Air.
- Avoid speculative claims when a tool could verify them.
- After you have enough information, respond directly and compactly.
- Your final output must be wrapped exactly once in <instruct>...</instruct>.
- Do not output JSON.
""".strip()


def build_instruct_agent(model: str) -> AgentSpec:
    return AgentSpec(
        name="instruct",
        model=model,
        system_prompt=INSTRUCT_SYSTEM_PROMPT,
    )


def build_instruct_handoff_input(
    *,
    user_prompt: str,
    stream_context: str,
    tool_catalog: list[str],
) -> str:
    tool_block = "\n".join(f"- {tool}" for tool in tool_catalog) if tool_catalog else "- No MCP tools are available."
    return f"""
User request:
{user_prompt}

Current stream context:
{stream_context}

Available tools:
{tool_block}

If a tool is useful, call it. When you have enough information, provide the final action block wrapped in <instruct>...</instruct>.
""".strip()


def build_instruct_finalize_input(
    *,
    user_prompt: str,
    stream_context: str,
    draft_response: str,
    tool_results: str,
) -> str:
    return f"""
Create the final action block for the stream.

User request:
{user_prompt}

Current stream context:
{stream_context}

Draft response from execution phase:
{draft_response or "(empty)"}

Tool transcript:
{tool_results or "(no tool results)"}

Return only a single <instruct>...</instruct> block.
""".strip()
