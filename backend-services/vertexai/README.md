# CoCo Agent (Vertex AI Backend)
このディレクトリは、CoCoエージェントのVertex AI Agent Engineバックエンドサービスを管理します。

## 🏗️ アーキテクチャ構成

本プロジェクトは **Google Agent Development Kit (ADK)** をベースに構築されていますが、Vertex AIへのデプロイに関して独自の構成を採用しています。

### エージェント構成
以下の2つのエージェントが独立した Agent Engine インスタンスとしてデプロイされます。

1. **Orchestrator Agent** (`app.agent_orchestrator`)
   - ユーザーからの自然言語クエリを受け付け、適切なサブエージェント（Monitor, Explorer, Reasoner）に振り分けるルーター役です。
   - ユーザーへの直接応答も行います。

2. **Monitor Agent** (`app.agent_monitor`)
   - カメラ映像の取得や画像を処理するための専門エージェントです。
   - Cloud Storage と連携して画像URIを取得します。

### コード構造
Vertex AIのAgent Engineは `app` ディレクトリ全体を1つのパッケージとして認識します。

```
vertexai/
├── app/
│   ├── __init__.py             # appパッケージ定義
│   ├── settings.py             # 環境変数定義 (Pydantic Settings)
│   ├── agent_orchestrator.py   # Orchestratorのエントリーポイント
│   ├── agent_monitor.py        # Monitorのエントリーポイント
│   ├── coco_agent/             # エージェントの実装本体
│   └── app_utils/              # ユーティリティ
├── deploy.py                   # 🚀 カスタムデプロイスクリプト (重要)
└── pyproject.toml              # 依存ライブラリ定義
```

---

## 🚀 デプロイ方法

本プロジェクトでは `make deploy` ではなく、**`deploy.py`** を使用してデプロイします。
このスクリプトは以下の処理を自動化します：

1. `requirements.txt` の自動生成（`uv export` 使用）
2. 生成した `requirements.txt` を `app/` ディレクトリ内に配置（これがないとクラウド側でライブラリがインストールされません）
3. `Orchestrator Agent` と `Monitor Agent` を順次デプロイ

### 実行コマンド

```bash
# 仮想環境内で実行することを推奨
uv run python deploy.py
```

> **Note:**
> 初回実行時は、Agent Engineの作成に 3〜5分 程度かかります。
> 2回目以降は、同名のインスタンスがあれば「更新」が行われます（冪等性担保）。

---

## 📦 開発環境セットアップ

```bash
# 依存関係のインストール
uv sync

# 環境変数の設定 (.env)
cp .env.example .env
# 必要な変数を記入: PROJECT_ID, GOOGLE_GENAI_USE_VERTEXAI=1 など
```
