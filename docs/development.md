# Development Workflow

This page focuses on the current repository workflow for local development, validation, and documentation maintenance.

## Local Setup

Install dependencies:

```bash
uv sync
```

Run the CLI:

```bash
uv run python src/main.py "Describe the current runtime flow."
```

## Recommended Development Loop

1. make a small focused change
2. run the required compile check
3. run the smallest relevant test
4. run a local CLI smoke check if runtime behavior changed
5. update documentation when behavior or setup changed

This matches the repository guidance to prefer incremental, debuggable changes.

## Verification Commands

Required compile check from [`AGENTS.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/AGENTS.md):

```bash
python3 -m py_compile src/main.py src/orchestrator/engine.py src/agents/*.py src/agents/__init__.py
```

Current unit tests:

```bash
python3 -m unittest tests/test_orchestrator_engine.py
```

What the current test file covers:

- `_coerce_stage_content()`
- `_sanitize_content()`
- `_join_stream()`

What it does not cover:

- live Ollama calls
- CLI behavior
- MCP server startup
- full end-to-end orchestration

## Runtime Smoke Testing

If you change runtime behavior, use the smallest local smoke test that exercises the affected path.

Examples:

```bash
uv run python src/main.py "Explain this project briefly."
uv run python src/main.py "このプロジェクトの流れを説明して"
uv run python src/main.py --trace "Explain the MCP startup behavior."
```

Before running these:

- ensure Ollama is installed
- ensure the configured model names exist locally

## Documentation Maintenance

When updating docs in this repository:

- describe only behavior visible in the current code
- mark inferred behavior explicitly
- avoid calling MCP "integrated" in a way that implies live tool execution unless that path exists
- keep stage names consistent with the code: `instruct`, `thinking`, `jp`
- keep examples short and runnable

## Open Development Gaps

- no bundled `.env.example`
- no documented model build or tagging workflow
- no integration tests for a live local stack
- no test covering MCP partial-failure behavior
