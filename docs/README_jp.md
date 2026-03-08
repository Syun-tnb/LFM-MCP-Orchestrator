# LFM-MCP-Orchestrator 日本語概要

このリポジトリは、Ollama 上の 3 つの役割を持つモデルを順番に実行するローカル向けオーケストレーターです。

- `instruct`: 正規化
- `thinking`: 推論
- `jp`: 最終日本語化

重要:

- 現在の実装は逐次実行です。旧説明にあるような並列実行ではありません。
- MCP サーバー接続基盤はありますが、現行パイプラインではツール呼び出しはまだ実行されません。

## 主要ドキュメント

- ルート概要とクイックスタート: [`README.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/README.md)
- アーキテクチャと baton flow: [`architecture.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/architecture.md)
- MCP の現状: [`mcp.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/mcp.md)
- 開発手順とテスト: [`development.md`](/Users/tanabeshunji/Documents/lfm-mcp-orchestrator/docs/development.md)

## 現在の実行フロー

コードから確認できる現在の流れ:

1. CLI が `.env` を読み込み、プロンプトと設定を解決する
2. Ollama への接続を確認する
3. 入力に日本語文字があれば `instruct` で英語の task memo に正規化する
4. `thinking` が英語で推論する
5. `jp` が `RESULT:` を使って自然な日本語の最終回答を返す

## ローカル実行

```bash
uv sync
uv run python src/main.py "このプロジェクトの流れを説明して"
```

前提:

- Python `>=3.14`
- `uv`
- `ollama`
- `lfm-thinking`, `lfm-instruct`, `lfm-jp` という名前で解決できるローカルモデル

不明点 / TODO:

- モデルの作成手順や Modelfile は現状リポジトリに含まれていません
- `.env.example` もまだありません
