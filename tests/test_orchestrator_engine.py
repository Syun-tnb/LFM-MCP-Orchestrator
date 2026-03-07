from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from orchestrator.engine import EMPTY_MODEL_RESPONSE, _coerce_stage_content, _join_stream, _sanitize_content


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


if __name__ == "__main__":
    unittest.main()
