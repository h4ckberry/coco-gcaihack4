# 実装計画 - プロンプトのリファクタリング

この計画では、Pythonのエージェント定義内にハードコードされているシステム指示（プロンプト）を、専用のMarkdownファイルに抽出する手順を概説します。これにより、コードに触れることなくプロンプトの調整が可能になり、保守性が向上します。

## 目標

現在、エージェントの指示は `agents/*.py` ファイル内の文字列としてハードコードされています。これらの文字列を `prompts/*.md` ファイルに移動し、それらを読み込むユーティリティを実装します。

## 提案される変更

### 1. プロンプトファイルの作成

`backend-services/vertexai/app/coco_agent/prompts/` ディレクトリに以下のMarkdownファイルを作成します。

#### [NEW] [explorer.md](file:///Users/eno/Workspace/Project/AIAgentHackathonwithGoogleCloud/coco-gcaihack4/backend-services/vertexai/app/coco_agent/prompts/explorer.md)
*   内容: `explorer.py` にある既存の指示文字列。

#### [NEW] [monitor.md](file:///Users/eno/Workspace/Project/AIAgentHackathonwithGoogleCloud/coco-gcaihack4/backend-services/vertexai/app/coco_agent/prompts/monitor.md)
*   内容: `monitor.py` にある既存の指示文字列。

#### [NEW] [reasoner.md](file:///Users/eno/Workspace/Project/AIAgentHackathonwithGoogleCloud/coco-gcaihack4/backend-services/vertexai/app/coco_agent/prompts/reasoner.md)
*   内容: `reasoner.py` にある既存の指示文字列。

#### [MODIFY] [orchestrator.md](file:///Users/eno/Workspace/Project/AIAgentHackathonwithGoogleCloud/coco-gcaihack4/backend-services/vertexai/app/coco_agent/prompts/orchestrator.md)
*   **アクション**: 既存の内容（プレースホルダーと思われる）を `orchestrator.py` の実際の指示で上書きします。

### 2. プロンプトローダーの実装

#### [NEW] [loader.py](file:///Users/eno/Workspace/Project/AIAgentHackathonwithGoogleCloud/coco-gcaihack4/backend-services/vertexai/app/coco_agent/prompts/loader.py)
*   **機能**:
    *   `load_prompt(prompt_name: str) -> str`: `prompts` ディレクトリから対応する `.md` ファイルを読み込み、文字列として返します。

### 3. エージェントの更新（ローダーの使用）

以下のファイルを修正し、`load_prompt` をインポートして `instruction` 引数に使用するようにします。

#### [MODIFY] [explorer.py](file:///Users/eno/Workspace/Project/AIAgentHackathonwithGoogleCloud/coco-gcaihack4/backend-services/vertexai/app/coco_agent/agents/explorer.py)
#### [MODIFY] [monitor.py](file:///Users/eno/Workspace/Project/AIAgentHackathonwithGoogleCloud/coco-gcaihack4/backend-services/vertexai/app/coco_agent/agents/monitor.py)
#### [MODIFY] [reasoner.py](file:///Users/eno/Workspace/Project/AIAgentHackathonwithGoogleCloud/coco-gcaihack4/backend-services/vertexai/app/coco_agent/agents/reasoner.py)
#### [MODIFY] [orchestrator.py](file:///Users/eno/Workspace/Project/AIAgentHackathonwithGoogleCloud/coco-gcaihack4/backend-services/vertexai/app/coco_agent/agents/orchestrator.py)

## 検証計画

### 自動テスト
*   エージェントが正常に初期化され、`instruction` 属性がファイルの内容と一致することを確認する簡単なスクリプトを実行します。
*   `python3 -m unittest backend-services/vertexai/tests/test_agents.py` (存在しない場合は作成するか、簡易チェックを実施)。

### 手動検証
*   ローカルでエージェントを実行し、`FileNotFoundError` やインポートエラーが発生しないことを確認します。
