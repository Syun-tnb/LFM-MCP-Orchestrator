from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any

from orchestrator.engine import (
    EMPTY_MODEL_RESPONSE,
    EngineConfig,
    ModelInvocationError,
    ModelTrace,
    TrinityOrchestrator,
)


def _chat_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(content=content))


def _generate_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(response=content)


class _FakeGateway:
    def __init__(self, *, chat_contents: list[str] | None = None, generate_contents: list[str] | None = None) -> None:
        self._chat_contents = list(chat_contents or [])
        self._generate_contents = list(generate_contents or [])
        self.chat_calls: list[dict[str, Any]] = []
        self.generate_calls: list[dict[str, Any]] = []

    async def chat(self, **kwargs: Any) -> tuple[Any, ModelTrace]:
        self.chat_calls.append(kwargs)
        next_item = self._chat_contents.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return _chat_response(next_item), ModelTrace(agent=kwargs["agent_name"], model=kwargs["model"], duration_ms=0)

    async def generate(self, **kwargs: Any) -> tuple[Any, ModelTrace]:
        self.generate_calls.append(kwargs)
        next_item = self._generate_contents.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return _generate_response(next_item), ModelTrace(agent=kwargs["agent_name"], model=kwargs["model"], duration_ms=0)


class _FakeToolRegistry:
    def __init__(self, warnings: list[str] | None = None) -> None:
        self.startup_warnings = list(warnings or [])


class TrinityOrchestratorFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_executes_normalize_thinking_and_jp_for_japanese_prompt(self) -> None:
        orchestrator = TrinityOrchestrator(
            EngineConfig(),
            tool_registry=_FakeToolRegistry(["filesystem unavailable"]),
        )
        orchestrator.gateway = _FakeGateway(
            chat_contents=[
                "```text\nTASK:\nDescribe the local runtime\n\nGOAL:\nExplain the flow\n\nCONSTRAINTS:\nNone\n```",
                "最終回答です。",
            ],
            generate_contents=[
                "SCRATCH:\nInspect stages\n\nRESULT:\nUse the local runtime flow.",
            ],
        )

        result = await orchestrator.run("ローカルLLMの構成を説明して", context={"cwd": "/tmp/demo"})

        self.assertEqual(result.action.content, "TASK:\nDescribe the local runtime\n\nGOAL:\nExplain the flow\n\nCONSTRAINTS:\nNone")
        self.assertEqual(result.reasoning.content, "SCRATCH:\nInspect stages\n\nRESULT:\nUse the local runtime flow.")
        self.assertEqual(result.final_response, "最終回答です。")
        self.assertEqual(result.warnings, ["filesystem unavailable"])
        self.assertEqual(len(result.traces), 3)
        self.assertEqual(len(orchestrator.gateway.chat_calls), 2)
        self.assertEqual(len(orchestrator.gateway.generate_calls), 1)
        self.assertIn("RUNTIME:", orchestrator.gateway.generate_calls[0]["prompt"])
        self.assertIn("CONTEXT:", orchestrator.gateway.generate_calls[0]["prompt"])
        self.assertEqual(
            result.stream,
            "TASK:\nDescribe the local runtime\n\nGOAL:\nExplain the flow\n\nCONSTRAINTS:\nNone\n---\nSCRATCH:\nInspect stages\n\nRESULT:\nUse the local runtime flow.\n---\n最終回答です。",
        )

    async def test_run_skips_normalize_for_english_prompt(self) -> None:
        orchestrator = TrinityOrchestrator(EngineConfig(), tool_registry=_FakeToolRegistry())
        orchestrator.gateway = _FakeGateway(
            chat_contents=["日本語で説明します。"],
            generate_contents=["RESULT:\nAnswer the request directly."],
        )

        result = await orchestrator.run("Summarize this essay.", context={"cwd": "/tmp/demo"})

        self.assertEqual(
            result.action.content,
            "TASK:\nSummarize this essay.\n\nGOAL:\nAnswer the request.\n\nCONSTRAINTS:\nNone",
        )
        self.assertEqual(len(orchestrator.gateway.chat_calls), 1)
        self.assertEqual(orchestrator.gateway.chat_calls[0]["agent_name"], "jp")
        self.assertEqual(len(orchestrator.gateway.generate_calls), 1)
        self.assertNotIn("RUNTIME:", orchestrator.gateway.generate_calls[0]["prompt"])
        self.assertNotIn("CONTEXT:", orchestrator.gateway.generate_calls[0]["prompt"])
        self.assertEqual(len(result.traces), 2)

    async def test_run_coerces_empty_or_malformed_stage_outputs(self) -> None:
        orchestrator = TrinityOrchestrator(EngineConfig(), tool_registry=_FakeToolRegistry())
        orchestrator.gateway = _FakeGateway(
            chat_contents=["   ", "```text\n   \n```"],
            generate_contents=["<think>hidden</think>"],
        )

        result = await orchestrator.run("日本語で要約して")

        self.assertEqual(result.action.content, EMPTY_MODEL_RESPONSE)
        self.assertEqual(result.reasoning.content, "hidden")
        self.assertEqual(result.final_response, EMPTY_MODEL_RESPONSE)
        self.assertEqual(
            result.stream,
            f"{EMPTY_MODEL_RESPONSE}\n---\nhidden\n---\n{EMPTY_MODEL_RESPONSE}",
        )

    async def test_run_propagates_model_invocation_errors(self) -> None:
        orchestrator = TrinityOrchestrator(EngineConfig(), tool_registry=_FakeToolRegistry())
        orchestrator.gateway = _FakeGateway(
            chat_contents=["日本語で説明します。"],
            generate_contents=[ModelInvocationError("thinking failed")],
        )

        with self.assertRaises(ModelInvocationError):
            await orchestrator.run("Explain the pipeline.")


if __name__ == "__main__":
    unittest.main()
