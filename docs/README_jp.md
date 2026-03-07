# LFM-MCP-Orchestrator 🧠🌸🛠️

M4 Air (24GB) 上で LFM 2.5 の 3 モデル（Instruct / Thinking / JP）を並列稼働させ、MCP (Model Context Protocol) を介して外部ツールと連携するための自前オーケストレーター。

## 🚀 Concept: 三位一体 (The Trinity)
本プロジェクトでは、特性の異なる 3 つの LFM (Liquid Foundation Models) を連携させ、一つの強力な思考体として運用します。

1. **lfm-thinking**: 論理構築・ステップバイステップの思考を担当。
2. **lfm-instruct**: 思考に基づいた具体的なタスク実行・コマンド生成を担当。
3. **lfm-jp**: シュンさんへの最終的なアウトプットと日本語最適化を担当。

## 🛠️ Tech Stack
- **Hardware**: MacBook Air M4 (24GB Unified Memory)
- **Runtime**: Python 3.14+ (via [uv](https://github.com/astral-sh/uv))
- **LLM Engine**: Ollama (LFM 2.5 1.2B Q8_0)
- **Protocol**: MCP (Model Context Protocol)

## 📁 Directory Structure
```text
src/
├── main.py              # エントリーポイント
├── orchestrator/        # 三姉妹の会議（推論リレー）制御
├── agents/              # 各モデルの役割・プロンプト定義
└── mcp/                 # MCPサーバーとの接続管理

```

## ⚡️ Quick Start

```bash
# 環境構築 (uv使用)
uv sync

# 実行
uv run src/main.py

```

---

© 2026 **Ashes Division(Syun) — Reyz Laboratory(Koharu)**

