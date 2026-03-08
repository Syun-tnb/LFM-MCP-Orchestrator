from __future__ import annotations

import unittest

from mcp_runtime.registry import (
    MCPToolDescriptor,
    MCPToolRegistry,
    ToolExecutionRecord,
    _ensure_unique_alias,
    _flatten_tool_content,
    _slugify,
)


class _DumpableItem:
    def model_dump_json(self, *, indent: int = 2) -> str:
        return '{\n  "structured": true\n}'


class _TextItem:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeAttachment:
    def __init__(self, record: ToolExecutionRecord) -> None:
        self.record = record
        self.calls: list[tuple[MCPToolDescriptor, dict[str, object]]] = []

    async def call_tool(self, descriptor: MCPToolDescriptor, arguments: dict[str, object]) -> ToolExecutionRecord:
        self.calls.append((descriptor, arguments))
        return self.record


class SlugifyTests(unittest.TestCase):
    def test_replaces_non_alphanumeric_characters(self) -> None:
        self.assertEqual(_slugify("Filesystem Server!"), "filesystem_server")

    def test_falls_back_to_tool_when_value_is_empty(self) -> None:
        self.assertEqual(_slugify("   "), "tool")


class EnsureUniqueAliasTests(unittest.TestCase):
    def test_returns_candidate_when_unused(self) -> None:
        self.assertEqual(_ensure_unique_alias("fs__read", set()), "fs__read")

    def test_appends_numeric_suffix_when_alias_is_taken(self) -> None:
        self.assertEqual(_ensure_unique_alias("fs__read", {"fs__read", "fs__read_2"}), "fs__read_3")


class FlattenToolContentTests(unittest.TestCase):
    def test_flattens_text_dumpable_and_json_content(self) -> None:
        content = _flatten_tool_content([_TextItem("alpha"), _DumpableItem(), {"beta": True}])

        self.assertEqual(content, 'alpha\n{\n  "structured": true\n}\n{"beta": true}')


class DescriptorAndRecordTests(unittest.TestCase):
    def test_descriptor_builds_ollama_tool_schema(self) -> None:
        descriptor = MCPToolDescriptor(
            alias="fs__read",
            name="read",
            server="filesystem",
            description="Read a file",
            input_schema={"properties": {"path": {"type": "string"}}},
        )

        tool = descriptor.as_ollama_tool()

        self.assertEqual(tool["function"]["name"], "fs__read")
        self.assertEqual(tool["function"]["parameters"]["type"], "object")
        self.assertIn("path", tool["function"]["parameters"]["properties"])

    def test_tool_execution_record_serializes_as_tool_message(self) -> None:
        record = ToolExecutionRecord(
            alias="fs__read",
            tool_name="read",
            server="filesystem",
            arguments={"path": "/tmp/demo.txt"},
            content="contents",
        )

        message = record.as_ollama_message()

        self.assertEqual(message["role"], "tool")
        self.assertEqual(message["tool_name"], "fs__read")
        self.assertIn('"path": "/tmp/demo.txt"', message["content"])


class RegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_render_catalog_and_call_tool_use_registered_descriptors(self) -> None:
        descriptor = MCPToolDescriptor(alias="fs__read", name="read", server="filesystem", description="Read a file")
        record = ToolExecutionRecord(alias="fs__read", tool_name="read", server="filesystem", content="contents")
        attachment = _FakeAttachment(record)
        registry = MCPToolRegistry([])
        registry._tools = {"fs__read": (attachment, descriptor)}

        self.assertEqual(
            registry.render_catalog(),
            ["fs__read: Read a file (server=filesystem, source=read)"],
        )
        self.assertEqual(registry.ollama_tools()[0]["function"]["name"], "fs__read")

        returned = await registry.call_tool("fs__read", {"path": "/tmp/demo.txt"})

        self.assertIs(returned, record)
        self.assertEqual(attachment.calls, [(descriptor, {"path": "/tmp/demo.txt"})])

    async def test_call_tool_raises_for_unknown_alias(self) -> None:
        registry = MCPToolRegistry([])

        with self.assertRaises(KeyError):
            await registry.call_tool("missing")


if __name__ == "__main__":
    unittest.main()
