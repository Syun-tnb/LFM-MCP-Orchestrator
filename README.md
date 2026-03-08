# LFM-MCP-Orchestrator

Local-first orchestrator for three Ollama-hosted LFM 2.5 roles:

- `thinking`
- `instruct`
- `jp`

The current code runs these stages sequentially, not in parallel. It targets a local Ollama setup and can attach to MCP servers over stdio.

## Status

This repository is early-stage. The documentation below describes current behavior implemented in code.

- Implemented:
  - CLI entry point in [`src/main.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/main.py)
  - three-stage orchestration in [`src/orchestrator/engine.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/orchestrator/engine.py)
  - prompt builders for `instruct`, `thinking`, and `jp`
  - MCP server attachment and tool catalog loading
- Not implemented yet:
  - model-parallel execution
  - tool calling from the orchestration pipeline
  - bundled model provisioning or Modelfiles

## Documentation

- Docs overview: [`docs/README.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/README.md)
- Architecture and baton flow: [`docs/architecture.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/architecture.md)
- MCP integration: [`docs/mcp.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/mcp.md)
- Development and testing: [`docs/development.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/development.md)
- Japanese overview: [`docs/README_jp.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/README_jp.md)

## Repository Layout

```text
src/
  agents/           Prompt builders and payload models for each stage
  mcp_runtime/      MCP server config, attachment, and tool registry
  orchestrator/     Engine config, orchestration flow, traces, helpers
  main.py           CLI entry point
tests/
  test_orchestrator_engine.py
docs/
  README.md
  architecture.md
  mcp.md
  development.md
  README_jp.md
```

## Quickstart

### 1. Requirements

- Python `>=3.14`
- [`uv`](https://github.com/astral-sh/uv)
- [`ollama`](https://ollama.com/)
- Ollama models available under these names, unless overridden:
  - `lfm-thinking`
  - `lfm-instruct`
  - `lfm-jp`

Current behavior inferred from code:

- The project is described as targeting a MacBook Air M4, but the code itself does not enforce macOS-only behavior.
- If `OLLAMA_HOST` points to a local host and Ollama is not running, the CLI tries to start `ollama serve` automatically.

### 2. Install dependencies

```bash
uv sync
```

### 3. Prepare environment

The CLI loads a local `.env` file automatically if present.

Minimum expected environment:

```bash
export OLLAMA_HOST=http://127.0.0.1:11434
export LFM_THINKING_MODEL=lfm-thinking
export LFM_INSTRUCT_MODEL=lfm-instruct
export LFM_JP_MODEL=lfm-jp
```

If your local model names differ, override them with the environment variables above.

### 4. Run the orchestrator

Pass the prompt as arguments:

```bash
uv run python src/main.py "ローカルLLM構成を説明して"
```

Read from a file:

```bash
uv run python src/main.py --prompt-file task.txt
```

Pipe input:

```bash
echo "Explain the current pipeline." | uv run python src/main.py
```

Print traces to `stderr`:

```bash
uv run python src/main.py --trace "Describe the runtime flow."
```

## Runtime Summary

Current behavior inferred from code:

1. The CLI loads environment variables, reads the prompt, builds `EngineConfig`, and ensures Ollama is reachable.
2. If the prompt contains Japanese characters, `instruct` runs as a normalization stage and produces a compact English task memo.
3. If the prompt does not contain Japanese characters, normalization is skipped and a synthetic task memo is created in code.
4. `thinking` receives the task memo and returns English reasoning with a `RESULT:` section.
5. `jp` receives the extracted `RESULT:` value and rewrites it into the final Japanese response.
6. Raw stage outputs and the accumulated baton are logged to `stderr`.

See [`docs/architecture.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/architecture.md) for the full flow.

## Configuration

Environment variables currently used by the code:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama base URL |
| `LFM_THINKING_MODEL` | `lfm-thinking` | Model name for the `thinking` stage |
| `LFM_INSTRUCT_MODEL` | `lfm-instruct` | Model name for the `instruct` stage |
| `LFM_JP_MODEL` | `lfm-jp` | Model name for the `jp` stage |
| `LFM_TARGET_LOCALE` | `ja-JP` | Locale passed into the finalizer prompt |
| `LFM_MAX_TOOL_ROUNDS` | `4` | Present in config, currently unused by the runtime |
| `LFM_REQUEST_TIMEOUT` | `180` | Ollama client timeout in seconds |
| `OLLAMA_KEEP_ALIVE` | `10m` | Ollama keep-alive hint |
| `LFM_ALLOW_PARTIAL_MCP` | `true` | Allow startup with partial MCP server failures |
| `MCP_SERVERS_JSON` | empty | Inline JSON list of MCP server definitions |

CLI options:

- `--prompt-file PATH`
- `--mcp-config PATH`
- `--trace`

## MCP Configuration

MCP server definitions can be supplied in either of these ways:

- `--mcp-config path/to/servers.json`
- `MCP_SERVERS_JSON='[...]'`

Example:

```json
[
  {
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    "enabled": true,
    "tool_prefix": "fs"
  }
]
```

Important current limitation:

- The MCP registry is initialized and tool metadata is loaded, but the orchestration path in [`src/orchestrator/engine.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/orchestrator/engine.py) does not currently expose tools to models or execute tool calls.
- As a result, `OrchestrationResult.tools` is currently always empty.

Details: [`docs/mcp.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/mcp.md)

## Troubleshooting

### `Ollama is not installed or not on PATH`

Install Ollama and confirm `ollama` is available in the shell used by `uv run`.

### `Ollama is not reachable`

- Check `OLLAMA_HOST`.
- If the host is remote, the CLI will not auto-start Ollama.
- If the host is local, try `ollama serve` manually and re-run.

### Model name errors

The repository does not currently ship model setup scripts or Modelfiles. Confirm that `ollama list` contains the names configured in `LFM_THINKING_MODEL`, `LFM_INSTRUCT_MODEL`, and `LFM_JP_MODEL`.

### Prompt normalization seems skipped

Current behavior inferred from code:

- normalization only runs when the input contains Japanese characters detected by a regex
- English-only prompts bypass the `instruct` normalization stage

### MCP server startup warnings

With `LFM_ALLOW_PARTIAL_MCP=true`, failed MCP attachments are recorded as warnings and startup continues. Use `--trace` to inspect warnings in the serialized result.

## Development

Required verification command from this repository:

```bash
python3 -m py_compile src/main.py src/orchestrator/engine.py src/agents/*.py src/agents/__init__.py
```

Unit tests currently present:

```bash
python3 -m unittest tests/test_orchestrator_engine.py
```

More details: [`docs/development.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/development.md)
