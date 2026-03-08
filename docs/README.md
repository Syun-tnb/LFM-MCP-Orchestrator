# Documentation Overview

This directory contains code-backed documentation for the current repository state.

## Read This First

- Root overview and quickstart: [`README.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/README.md)
- Runtime architecture and baton flow: [`architecture.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/architecture.md)
- MCP integration details and limits: [`mcp.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/mcp.md)
- Development workflow and tests: [`development.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/development.md)
- Japanese overview: [`README_jp.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/README_jp.md)

## What These Docs Cover

- what the orchestrator currently does
- how the three stages are wired
- how to run the CLI locally
- which environment variables and CLI flags matter
- what MCP support exists today
- how to verify changes without broad or unnecessary testing

## Documentation Rules Used Here

- Prefer current behavior over intended future design.
- Mark uncertain items explicitly.
- Keep terminology consistent with the code:
  - `instruct` is the normalization stage
  - `thinking` is the reasoning stage
  - `jp` is the final Japanese answer stage
  - `baton` refers to the accumulated stage output stream logged by the engine

## Known Gaps

- No bundled model provisioning instructions yet
- No example `.env` file yet
- No end-to-end runtime smoke test covering a live Ollama instance
