from __future__ import annotations

import asyncio
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import main


class LoadPromptTests(unittest.TestCase):
    def test_reads_prompt_from_file_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_file = Path(temp_dir) / "prompt.txt"
            prompt_file.write_text("  file prompt  ", encoding="utf-8")

            result = main.load_prompt(Namespace(prompt=[], prompt_file=prompt_file))

        self.assertEqual(result, "file prompt")

    def test_reads_prompt_from_cli_arguments(self) -> None:
        args = Namespace(prompt=["Explain", "the", "pipeline"], prompt_file=None)

        self.assertEqual(main.load_prompt(args), "Explain the pipeline")

    def test_reads_prompt_from_stdin_when_available(self) -> None:
        args = Namespace(prompt=[], prompt_file=None)
        fake_stdin = io.StringIO("  piped prompt  ")

        with patch.object(main.sys, "stdin", fake_stdin):
            with patch.object(fake_stdin, "isatty", return_value=False):
                self.assertEqual(main.load_prompt(args), "piped prompt")

    def test_raises_when_no_prompt_source_is_available(self) -> None:
        args = Namespace(prompt=[], prompt_file=None)
        fake_stdin = io.StringIO("")

        with patch.object(main.sys, "stdin", fake_stdin):
            with patch.object(fake_stdin, "isatty", return_value=True):
                with self.assertRaises(SystemExit):
                    main.load_prompt(args)


class LoadMcpServersTests(unittest.TestCase):
    def test_loads_server_definitions_from_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "mcp.json"
            config_path.write_text(
                json.dumps([{"name": "fs", "command": "npx", "args": ["server"]}]),
                encoding="utf-8",
            )

            servers = main.load_mcp_servers(config_path)

        self.assertIsNotNone(servers)
        self.assertEqual(servers[0].name, "fs")
        self.assertEqual(servers[0].args, ["server"])

    def test_returns_none_when_path_is_missing(self) -> None:
        self.assertIsNone(main.load_mcp_servers(None))


class HostHelperTests(unittest.TestCase):
    def test_normalize_host_adds_scheme_when_missing(self) -> None:
        self.assertEqual(main._normalize_host("127.0.0.1:11434/"), "http://127.0.0.1:11434")

    def test_is_local_host_detects_loopback_aliases(self) -> None:
        self.assertTrue(main._is_local_host("localhost:11434"))
        self.assertFalse(main._is_local_host("https://example.com"))


class EnsureOllamaReadyTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_none_when_ollama_is_already_reachable(self) -> None:
        with patch.object(main, "_probe_ollama", AsyncMock(return_value=True)):
            self.assertIsNone(await main.ensure_ollama_ready("http://127.0.0.1:11434"))

    async def test_rejects_remote_hosts_when_unreachable(self) -> None:
        with patch.object(main, "_probe_ollama", AsyncMock(return_value=False)):
            with self.assertRaises(SystemExit) as ctx:
                await main.ensure_ollama_ready("https://example.com")

        self.assertIn("Auto-bootstrap is only supported for local hosts", str(ctx.exception))

    async def test_raises_clear_error_when_ollama_binary_is_missing(self) -> None:
        with patch.object(main, "_probe_ollama", AsyncMock(return_value=False)):
            with patch.object(main.asyncio, "create_subprocess_exec", side_effect=FileNotFoundError):
                with self.assertRaises(SystemExit) as ctx:
                    await main.ensure_ollama_ready("127.0.0.1:11434")

        self.assertIn("not installed or not on PATH", str(ctx.exception))

    async def test_bootstraps_local_ollama_until_probe_succeeds(self) -> None:
        process = SimpleNamespace(returncode=None)
        probe = AsyncMock(side_effect=[False, True])

        with patch.object(main, "_probe_ollama", probe):
            with patch.object(main.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)):
                returned = await main.ensure_ollama_ready("127.0.0.1:11434")

        self.assertIs(returned, process)


if __name__ == "__main__":
    unittest.main()
