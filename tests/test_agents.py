from __future__ import annotations

import unittest

from agents import RuntimeConstraints
from agents.instruct import INSTRUCT_SYSTEM_PROMPT, build_instruct_agent, build_instruct_normalize_input
from agents.jp import JP_SYSTEM_PROMPT, build_jp_agent, build_jp_input
from agents.thinking import THINKING_SYSTEM_PROMPT, build_thinking_agent, build_thinking_input


class InstructAgentTests(unittest.TestCase):
    def test_build_instruct_agent_sets_expected_metadata(self) -> None:
        agent = build_instruct_agent("lfm-instruct-test")

        self.assertEqual(agent.name, "instruct")
        self.assertEqual(agent.model, "lfm-instruct-test")
        self.assertEqual(agent.system_prompt, INSTRUCT_SYSTEM_PROMPT)

    def test_normalize_input_uses_fixed_label_schema(self) -> None:
        prompt = build_instruct_normalize_input(user_prompt="日本語の依頼")

        self.assertIn("SOURCE:\n日本語の依頼", prompt)
        self.assertIn("TASK:\n<one short line>", prompt)
        self.assertIn("GOAL:\n<one short line>", prompt)
        self.assertIn('CONSTRAINTS:\n<one short line or "None">', prompt)
        self.assertIn("Do not answer.", prompt)
        self.assertIn("Return only the memo.", prompt)


class ThinkingAgentTests(unittest.TestCase):
    def test_build_thinking_agent_sets_expected_metadata(self) -> None:
        agent = build_thinking_agent("lfm-thinking-test")

        self.assertEqual(agent.name, "thinking")
        self.assertEqual(agent.model, "lfm-thinking-test")
        self.assertEqual(agent.system_prompt, THINKING_SYSTEM_PROMPT)

    def test_build_thinking_input_includes_runtime_and_sorted_context_when_requested(self) -> None:
        prompt = build_thinking_input(
            task_memo="TASK:\nInvestigate pipeline",
            constraints=RuntimeConstraints(),
            context={"zeta": 2, "alpha": 1},
            include_runtime_context=True,
        )

        self.assertIn("TASK_MEMO:\nTASK:\nInvestigate pipeline", prompt)
        self.assertIn("RUNTIME:\n{", prompt)
        self.assertIn('"alpha": 1', prompt)
        self.assertLess(prompt.index('"alpha": 1'), prompt.index('"zeta": 2'))
        self.assertIn("OUTPUT:\nSCRATCH:", prompt)
        self.assertIn("RESULT:\n<one concise English conclusion>", prompt)

    def test_build_thinking_input_omits_runtime_context_when_not_requested(self) -> None:
        prompt = build_thinking_input(
            task_memo="TASK:\nInvestigate pipeline",
            constraints=RuntimeConstraints(),
            context=None,
            include_runtime_context=False,
        )

        self.assertNotIn("RUNTIME:", prompt)
        self.assertNotIn("CONTEXT:", prompt)


class JPAgentTests(unittest.TestCase):
    def test_build_jp_agent_sets_expected_metadata(self) -> None:
        agent = build_jp_agent("lfm-jp-test")

        self.assertEqual(agent.name, "jp")
        self.assertEqual(agent.model, "lfm-jp-test")
        self.assertEqual(agent.system_prompt, JP_SYSTEM_PROMPT)

    def test_build_jp_input_keeps_result_and_reference_fields(self) -> None:
        prompt = build_jp_input(
            user_prompt="Explain the runtime flow.",
            locale="ja-JP",
            reasoning_result="Use the local pipeline.",
        )

        self.assertIn("RESULT:\nUse the local pipeline.", prompt)
        self.assertIn("REQUEST: Explain the runtime flow.", prompt)
        self.assertIn("LOCALE: ja-JP", prompt)
        self.assertIn("Do not add new facts.", prompt)
        self.assertIn("Preserve commands, file paths, and identifiers exactly.", prompt)


if __name__ == "__main__":
    unittest.main()
