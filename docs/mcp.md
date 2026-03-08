# MCP Integration Overview

This page describes the MCP support implemented in [`src/mcp_runtime/registry.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/mcp_runtime/registry.py) and how it is used by the orchestrator today.

## Current State

Implemented:

- parse MCP server definitions
- launch stdio MCP servers
- initialize client sessions
- list tools from each attached server
- generate unique tool aliases
- record startup warnings

Not yet wired into the main orchestration path:

- passing tool schemas into model calls
- accepting tool calls from model output
- executing tools during a run
- populating `OrchestrationResult.tools` with live executions

That limitation is important. The repository already has MCP attachment infrastructure, but the current runtime behaves as a tool-disabled pipeline.

## Configuration Sources

You can provide MCP server definitions in two ways:

### CLI file

```bash
uv run python src/main.py --mcp-config servers.json "..."
```

### Environment variable

```bash
export MCP_SERVERS_JSON='[...]'
```

When both are relevant:

- `--mcp-config` is passed directly into `EngineConfig.from_env(mcp_servers=...)`
- `MCP_SERVERS_JSON` is only read when no explicit MCP server list is supplied

## MCP Server Schema

Each server definition maps to `MCPServerConfig`:

```json
{
  "name": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
  "env": {
    "EXAMPLE_FLAG": "1"
  },
  "cwd": "/absolute/path",
  "description": "Optional description",
  "enabled": true,
  "tool_prefix": "fs"
}
```

Field meanings:

- `name`: server identifier used in warnings and alias generation
- `command`: executable to launch
- `args`: command arguments
- `env`: optional environment overrides
- `cwd`: optional working directory
- `description`: optional descriptive text
- `enabled`: skip startup when `false`
- `tool_prefix`: override the alias prefix used for exposed tools

## Startup Behavior

During `TrinityOrchestrator.__aenter__()`:

1. `MCPToolRegistry.start()` is called.
2. Each enabled server is started concurrently with `asyncio.gather()`.
3. The registry initializes the MCP session and lists tools.
4. Tool names are slugified and prefixed to create unique aliases.
5. Startup failures are collected as warnings.

If `LFM_ALLOW_PARTIAL_MCP=true`:

- failed servers do not stop startup
- warnings are stored in `tool_registry.startup_warnings`

If `LFM_ALLOW_PARTIAL_MCP=false`:

- any MCP startup failure raises and aborts orchestrator startup

## Tool Alias Format

Tool aliases are generated like this:

```text
<prefix>__<tool_name>
```

If an alias collides, numeric suffixes are added:

```text
fs__read_file
fs__read_file_2
```

This matters if future runtime code starts exposing the tool catalog directly to the models.

## What the Runtime Does Not Yet Do

Current behavior inferred from code:

- the engine constructs `MCPToolRegistry`, but `TrinityOrchestrator.run()` never calls `render_catalog()`, `ollama_tools()`, or `call_tool()`
- `ToolExecutionRecord` exists but is not produced by the normal execution path
- `EngineConfig.max_tool_rounds` is present but currently unused

## Practical Guidance

If you are only trying to run the current orchestrator locally:

- MCP setup is optional
- skip MCP entirely unless you are developing the registry layer or preparing future tool execution work

If you are extending MCP support:

- start in [`src/orchestrator/engine.py`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/src/orchestrator/engine.py)
- decide how tool schemas will be exposed to the `thinking` or `instruct` stages
- define where tool execution records should be added to `OrchestrationResult.tools`
- add a small integration test around partial startup and at least one tool call path
