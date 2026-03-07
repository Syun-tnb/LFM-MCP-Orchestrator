from __future__ import annotations

import argparse
import asyncio
import json
import sys
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from dotenv import load_dotenv

from mcp_runtime import MCPServerConfig
from orchestrator import EngineConfig, TrinityOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the LFM Trinity orchestrator.")
    parser.add_argument("prompt", nargs="*", help="Prompt to send to the orchestrator.")
    parser.add_argument("--prompt-file", type=Path, help="Read the prompt from a file.")
    parser.add_argument("--mcp-config", type=Path, help="JSON file containing MCP server definitions.")
    parser.add_argument("--trace", action="store_true", help="Print orchestration metadata as JSON.")
    return parser.parse_args()


def load_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file is not None:
        return args.prompt_file.read_text(encoding="utf-8").strip()

    prompt = " ".join(args.prompt).strip()
    if prompt:
        return prompt

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    raise SystemExit("Provide a prompt, --prompt-file, or pipe input on stdin.")


def load_mcp_servers(path: Path | None) -> list[MCPServerConfig] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [MCPServerConfig.model_validate(item) for item in payload]


def _normalize_host(raw_host: str) -> str:
    parsed = urlparse(raw_host)
    if parsed.scheme:
        return raw_host.rstrip("/")
    return f"http://{raw_host.rstrip('/')}"


def _is_local_host(raw_host: str) -> bool:
    parsed = urlparse(_normalize_host(raw_host))
    return (parsed.hostname or "").lower() in {"127.0.0.1", "localhost", "0.0.0.0", "::1"}


async def _probe_ollama(raw_host: str, *, timeout: float = 1.5) -> bool:
    base_url = _normalize_host(raw_host)

    def _request() -> bool:
        with urlopen(f"{base_url}/api/tags", timeout=timeout) as response:
            return 200 <= getattr(response, "status", 500) < 500

    try:
        return await asyncio.to_thread(_request)
    except Exception:
        return False


async def ensure_ollama_ready(raw_host: str, *, startup_timeout: float = 30.0) -> asyncio.subprocess.Process | None:
    if await _probe_ollama(raw_host):
        return None

    if not _is_local_host(raw_host):
        raise SystemExit(f"Ollama is not reachable at {raw_host}. Auto-bootstrap is only supported for local hosts.")

    try:
        process = await asyncio.create_subprocess_exec(
            "ollama",
            "serve",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit("Ollama is not installed or not on PATH, so auto-bootstrap cannot start it.") from exc

    deadline = asyncio.get_running_loop().time() + startup_timeout
    last_returncode: int | None = None
    while asyncio.get_running_loop().time() < deadline:
        if await _probe_ollama(raw_host):
            return process
        if process.returncode is not None:
            last_returncode = process.returncode
        await asyncio.sleep(0.5)

    with suppress(ProcessLookupError):
        if process.returncode is None:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=2)

    if last_returncode is not None:
        raise SystemExit(f"Ollama failed to start and exited with code {last_returncode}.")
    raise SystemExit(f"Ollama did not become ready at {raw_host} within {startup_timeout:.0f} seconds.")


async def async_main() -> int:
    load_dotenv()
    args = parse_args()
    prompt = load_prompt(args)
    config = EngineConfig.from_env(mcp_servers=load_mcp_servers(args.mcp_config))
    await ensure_ollama_ready(config.ollama_host)

    async with TrinityOrchestrator(config) as orchestrator:
        result = await orchestrator.run(prompt)

    print(result.final_response)
    if args.trace:
        print(result.model_dump_json(indent=2), file=sys.stderr)
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
