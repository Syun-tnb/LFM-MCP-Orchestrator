from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

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
    if args.prompt_file:
        return args.prompt_file.read_text(encoding="utf-8").strip()
    if args.prompt:
        return " ".join(args.prompt).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    raise SystemExit("Provide a prompt, --prompt-file, or pipe input on stdin.")


def load_mcp_servers(path: Path | None) -> list[MCPServerConfig] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [MCPServerConfig.model_validate(item) for item in payload]


async def async_main() -> int:
    load_dotenv()
    args = parse_args()
    prompt = load_prompt(args)
    config = EngineConfig.from_env(mcp_servers=load_mcp_servers(args.mcp_config))

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
