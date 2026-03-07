from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RuntimeConstraints(BaseModel):
    hardware: str = "MacBook Air M4 (24GB Unified Memory)"
    runtime: str = "Python 3.14+ via uv"
    llm_engine: str = "Ollama"
    protocol: str = "MCP"
    principle: str = "Local-first orchestration for The Trinity"


class AgentSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    model: str
    system_prompt: str
    options: dict[str, Any] = Field(default_factory=dict)


class TrinityAgents(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    thinking: AgentSpec
    instruct: AgentSpec
    jp: AgentSpec


from .instruct import (
    ActionPayload,
    build_instruct_agent,
    build_instruct_normalize_input,
)
from .jp import (
    LocalizedPayload,
    build_jp_agent,
    build_jp_input,
)
from .thinking import ThinkingPayload, build_thinking_agent, build_thinking_input

__all__ = [
    "ActionPayload",
    "AgentSpec",
    "LocalizedPayload",
    "RuntimeConstraints",
    "ThinkingPayload",
    "TrinityAgents",
    "build_instruct_agent",
    "build_instruct_normalize_input",
    "build_jp_agent",
    "build_jp_input",
    "build_thinking_agent",
    "build_thinking_input",
]
