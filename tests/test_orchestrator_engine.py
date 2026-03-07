from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from orchestrator.engine import EMPTY_MODEL_RESPONSE, _extract_tagged_block, _sanitize_content


class ExtractTaggedBlockTests(unittest.TestCase):
    def test_extracts_requested_tag_and_sanitizes_nested_tags(self) -> None:
        raw = """
        <reasoning>ignore this</reasoning>
        <instruct>
            <reasoning>nested plan</reasoning>
            final action text
        </instruct>
        """

        self.assertEqual(_extract_tagged_block(raw, "instruct"), "nested plan\nfinal action text")

    def test_falls_back_to_any_tag_when_requested_tag_is_missing(self) -> None:
        raw = "  <response> wrapped fallback payload </response>  "

        self.assertEqual(_extract_tagged_block(raw, "instruct"), "wrapped fallback payload")

    def test_falls_back_to_sanitized_raw_text_when_no_tags_exist(self) -> None:
        raw = "  plain fallback text with no wrappers  "

        self.assertEqual(_extract_tagged_block(raw, "instruct"), "plain fallback text with no wrappers")

    def test_prefers_requested_tag_when_multiple_different_tags_are_present(self) -> None:
        raw = """
        <reasoning>first block</reasoning>
        <instruct>second block</instruct>
        <response>third block</response>
        """

        self.assertEqual(_extract_tagged_block(raw, "instruct"), "second block")

    def test_handles_code_fences_and_whitespace(self) -> None:
        raw = """
        ```xml
        <instruct>
            trimmed content
        </instruct>
        ```
        """

        self.assertEqual(_extract_tagged_block(raw, "instruct"), "trimmed content")

    def test_returns_default_string_on_empty_content(self) -> None:
        self.assertEqual(_extract_tagged_block("   ", "instruct"), EMPTY_MODEL_RESPONSE)

    def test_returns_default_string_on_empty_tagged_content(self) -> None:
        raw = "<response>   </response>"

        self.assertEqual(_extract_tagged_block(raw, "response"), EMPTY_MODEL_RESPONSE)


class SanitizeContentTests(unittest.TestCase):
    def test_strips_stage_tags_and_outer_whitespace(self) -> None:
        raw = "  <reasoning> alpha </reasoning>  "

        self.assertEqual(_sanitize_content(raw), "alpha")

    def test_strips_mixed_tags_from_dirty_input(self) -> None:
        raw = """
        <reasoning>plan</reasoning>
        <instruct>execute</instruct>
        <response>answer</response>
        """

        self.assertEqual(_sanitize_content(raw), "plan\nexecute\nanswer")

    def test_strips_code_fences_before_removing_tags(self) -> None:
        raw = """
        ```xml
        <instruct>clean me</instruct>
        ```
        """

        self.assertEqual(_sanitize_content(raw), "clean me")

    def test_collapses_excess_blank_lines(self) -> None:
        raw = "<instruct>line one\n\n\n\nline two</instruct>"

        self.assertEqual(_sanitize_content(raw), "line one\n\nline two")

    def test_removes_nested_tags_but_keeps_text_content(self) -> None:
        raw = "<instruct><reasoning>echoed old tag</reasoning> plain action text</instruct>"

        self.assertEqual(_sanitize_content(raw), "echoed old tag plain action text")


if __name__ == "__main__":
    unittest.main()
