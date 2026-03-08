# Architecture Overview

This page describes the orchestration pipeline implemented today in [`src/orchestrator/engine.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/orchestrator/engine.py).

## High-Level Flow

The runtime is sequential:

1. load prompt and config
2. ensure Ollama is reachable
3. optionally normalize the prompt with `instruct`
4. reason with `thinking`
5. finalize in Japanese with `jp`

Current behavior inferred from code:

- despite older documentation language, the three model roles are not executed in parallel
- MCP servers are attached during orchestrator startup, but tools are not used in the main pipeline yet

## Main Components

### CLI

[`src/main.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/main.py)

- parses prompt input from args, file, or stdin
- loads `.env`
- loads MCP server config from `--mcp-config` if provided
- builds `EngineConfig`
- auto-starts local Ollama when possible
- prints the final Japanese response to `stdout`
- prints optional trace JSON to `stderr` with `--trace`

### Orchestrator Engine

[`src/orchestrator/engine.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/orchestrator/engine.py)

- defines `EngineConfig`
- initializes `TrinityOrchestrator`
- owns the stage execution order
- records traces, warnings, and stage outputs
- sanitizes model outputs before passing them on

### Agent Prompt Builders

[`src/agents/instruct.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/agents/instruct.py)

- builds the normalization prompt
- asks for a compact English memo with fixed labels

[`src/agents/thinking.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/agents/thinking.py)

- builds the reasoning prompt
- can include runtime constraints
- can append a JSON `CONTEXT:` block when the Python API provides context

[`src/agents/jp.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/agents/jp.py)

- builds the final Japanese answer prompt
- forbids adding new facts

### MCP Runtime

[`src/mcp_runtime/registry.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/mcp_runtime/registry.py)

- defines MCP server config
- launches stdio MCP servers
- fetches tool metadata
- creates unique tool aliases
- stores startup warnings

## Stage Responsibilities

### `instruct`

Responsibility:

- normalize Japanese-like user input into a short English task memo

Output shape:

```text
TASK:
...

GOAL:
...

CONSTRAINTS:
...
```

Current behavior inferred from code:

- this stage is only called when the input contains Japanese characters
- English-only prompts skip this stage and use a synthetic memo generated in code

### `thinking`

Responsibility:

- take the task memo and produce English reasoning

Expected prompt sections:

```text
TASK_MEMO:
...

RUNTIME:
...

CONTEXT:
...

OUTPUT:
SCRATCH:
...

RESULT:
...
```

Notes:

- `RUNTIME:` is only included when the user prompt contains runtime-related keywords
- `CONTEXT:` is only available through the Python API, not the CLI
- the engine later extracts `RESULT:` when building the input for `jp`

### `jp`

Responsibility:

- convert the reasoning result into the final Japanese user-facing answer

Rules enforced in the prompt:

- preserve the meaning of `RESULT`
- do not add new facts
- do not mention scratch reasoning or the pipeline
- preserve commands, file paths, and identifiers exactly

## Baton Flow

The engine maintains `stream_blocks`, which act as the current baton.

Current behavior inferred from code:

- the baton is an accumulated text stream, not a shared structured message history
- each stage receives a purpose-built prompt, not the entire previous conversation
- the baton is joined with `---` separators via `_join_stream()`
- the baton is logged to `stderr` after each stage

Example shape:

```text
TASK:
...
---
SCRATCH:
...

RESULT:
...
---
最終的な日本語の回答
```

## Language Handling

Prompt language detection is simple:

- if the prompt contains Japanese characters, `detect_prompt_language()` returns `ja`
- otherwise it returns `en`

Implication:

- mixed-language prompts may still route through the Japanese normalization path if they include any Japanese characters

## Runtime Context Injection

The `thinking` stage only receives the `RUNTIME:` block when the raw prompt includes keywords such as:

- `ollama`
- `mcp`
- `runtime`
- `pipeline`
- `workflow`
- Japanese equivalents listed in `RUNTIME_KEYWORDS`

This is a keyword heuristic, not semantic routing.

## Result Object

`TrinityOrchestrator.run()` returns `OrchestrationResult` with:

- `request`
- `locale`
- `reasoning`
- `action`
- `localized`
- `stream`
- `tools`
- `warnings`
- `traces`
- `started_at`
- `completed_at`

Current behavior inferred from code:

- `final_response` is `localized.content`
- `tools` is currently always empty because tool execution is not wired into the pipeline

## Logging and Traces

The engine logs raw stage output and baton state to `stderr`:

- `=== RAW ... OUTPUT ===`
- `=== BATON AFTER ... ===`

With `--trace`, the CLI also prints serialized `OrchestrationResult` JSON to `stderr`.

## Known Limitations

- no parallel stage execution
- no MCP tool execution in the main loop
- no streaming token output to the terminal
- no bundled model creation flow
