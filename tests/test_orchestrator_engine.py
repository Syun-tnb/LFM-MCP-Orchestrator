from __future__ import annotations

import unittest
from unittest.mock import patch

from mcp_runtime import MCPServerConfig
from orchestrator.engine import (
    EMPTY_MODEL_RESPONSE,
    EngineConfig,
    _build_passthrough_task_memo,
    _coerce_stage_content,
    _extract_result_content,
    _join_stream,
    _sanitize_content,
    _should_include_runtime_context,
    detect_prompt_language,
)


class CoerceStageContentTests(unittest.TestCase):
    def test_returns_trimmed_plain_text(self) -> None:
        raw = "  plain fallback text with no wrappers  "

        self.assertEqual(_coerce_stage_content(raw), "plain fallback text with no wrappers")

    def test_strips_code_fences_and_whitespace(self) -> None:
        raw = """
        ```text
            trimmed content
        ```
        """

        self.assertEqual(_coerce_stage_content(raw), "trimmed content")

    def test_returns_default_string_on_empty_content(self) -> None:
        self.assertEqual(_coerce_stage_content("   "), EMPTY_MODEL_RESPONSE)

    def test_preserves_mixed_plain_text_lines(self) -> None:
        raw = """
        first block

        second block
        third block
        """

        self.assertEqual(_coerce_stage_content(raw), "first block\n\nsecond block\nthird block")


class SanitizeContentTests(unittest.TestCase):
    def test_trims_outer_whitespace(self) -> None:
        raw = "  alpha  "

        self.assertEqual(_sanitize_content(raw), "alpha")

    def test_preserves_mixed_plain_text_from_dirty_input(self) -> None:
        raw = """
        plan
          execute
        answer
        """

        self.assertEqual(_sanitize_content(raw), "plan\nexecute\nanswer")

    def test_strips_code_fences_before_normalizing_text(self) -> None:
        raw = """
        ```text
        clean me
        ```
        """

        self.assertEqual(_sanitize_content(raw), "clean me")

    def test_collapses_excess_blank_lines(self) -> None:
        raw = "<instruct>line one\n\n\n\nline two</instruct>"

        self.assertEqual(_sanitize_content(raw), "line one\n\nline two")

    def test_keeps_plain_text_markers_as_literal_content(self) -> None:
        raw = "[thinking]\nplain action text\n[end]"

        self.assertEqual(_sanitize_content(raw), "[thinking]\nplain action text\n[end]")


class JoinStreamTests(unittest.TestCase):
    def test_uses_stage_separator(self) -> None:
        blocks = ["reasoning brief", "execution output", "final response"]

        self.assertEqual(_join_stream(blocks), "reasoning brief\n---\nexecution output\n---\nfinal response")


class DetectPromptLanguageTests(unittest.TestCase):
    def test_detects_japanese_text(self) -> None:
        self.assertEqual(detect_prompt_language("日本語で説明して"), "ja")

    def test_defaults_to_english_when_no_japanese_characters_are_present(self) -> None:
        self.assertEqual(detect_prompt_language("Explain the current pipeline."), "en")


class PassthroughTaskMemoTests(unittest.TestCase):
    def test_builds_compact_task_memo_for_non_japanese_prompts(self) -> None:
        memo = _build_passthrough_task_memo("  Explain   the\n pipeline.  ")

        self.assertEqual(
            memo,
            "TASK:\nExplain the pipeline.\n\nGOAL:\nAnswer the request.\n\nCONSTRAINTS:\nNone",
        )


class RuntimeContextKeywordTests(unittest.TestCase):
    def test_matches_english_runtime_keywords(self) -> None:
        self.assertTrue(_should_include_runtime_context("Describe the MCP workflow."))

    def test_matches_japanese_runtime_keywords(self) -> None:
        self.assertTrue(_should_include_runtime_context("ローカルLLMの構成を説明して"))

    def test_ignores_unrelated_prompts(self) -> None:
        self.assertFalse(_should_include_runtime_context("Summarize this poem."))


class ExtractResultContentTests(unittest.TestCase):
    def test_prefers_explicit_result_block(self) -> None:
        raw = """
        SCRATCH:
        analyze

        RESULT:
        concise answer

        NOTES:
        trailing text
        """

        self.assertEqual(_extract_result_content(raw), "concise answer")

    def test_falls_back_to_last_non_empty_block(self) -> None:
        raw = """
        interim thought

        final usable answer
        """

        self.assertEqual(_extract_result_content(raw), "final usable answer")

    def test_returns_default_string_when_no_content_remains(self) -> None:
        self.assertEqual(_extract_result_content("   "), EMPTY_MODEL_RESPONSE)


class EngineConfigFromEnvTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "MCP_SERVERS_JSON": '[{"name":"filesystem","command":"npx","args":["server"],"tool_prefix":"fs"}]',
            "LFM_TARGET_LOCALE": "ja-JP",
        },
        clear=False,
    )
    def test_parses_mcp_servers_json(self) -> None:
        config = EngineConfig.from_env()

        self.assertEqual(len(config.mcp_servers), 1)
        self.assertEqual(config.mcp_servers[0].name, "filesystem")
        self.assertEqual(config.mcp_servers[0].tool_prefix, "fs")

    @patch.dict("os.environ", {"MCP_SERVERS_JSON": "[]"}, clear=False)
    def test_prefers_explicit_mcp_servers_argument(self) -> None:
        explicit_servers = [MCPServerConfig(name="explicit", command="python")]

        config = EngineConfig.from_env(mcp_servers=explicit_servers)

        self.assertEqual(config.mcp_servers, explicit_servers)


if __name__ == "__main__":
    unittest.main()
