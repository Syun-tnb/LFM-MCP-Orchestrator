# LFM-MCP-Orchestrator 🧠🌸🛠️

An autonomous orchestrator designed to run a trio of LFM 2.5 models (Instruct / Thinking / JP) in parallel on M4 Air (24GB), integrated with external tools via MCP (Model Context Protocol).

## 🚀 Concept: The Trinity
This project orchestrates three distinct Liquid Foundation Models (LFM) to function as a single, powerful cognitive entity.

1. **lfm-thinking**: Responsible for logical construction and step-by-step reasoning.
2. **lfm-instruct**: Translates reasoning into actionable tasks and command generation.
3. **lfm-jp**: Handles final output optimization and localization for the user (Syun).

## 🛠️ Tech Stack
- **Hardware**: MacBook Air M4 (24GB Unified Memory)
- **Runtime**: Python 3.14+ (via [uv](https://github.com/astral-sh/uv))
- **LLM Engine**: Ollama (LFM 2.5 1.2B Q8_0)
- **Protocol**: MCP (Model Context Protocol)

## 📁 Directory Structure
```text
src/
├── main.py              # Entry point
├── orchestrator/        # The "Meeting" logic (inference relay control)
├── agents/              # Role & prompt definitions for each model
└── mcp/                 # MCP server connection management

```

## ⚡️ Quick Start

```bash
# Setup environment (via uv)
uv sync

# Run
uv run src/main.py

```

---

© 2026 **Ashes Division(Syun) — Reyz Laboratory(Koharu)**

