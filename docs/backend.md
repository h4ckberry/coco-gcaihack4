# Agent Architecture Specification

## 1. システム概要
本システムは、物理空間の監視・探索・推論を行うマルチエージェントシステムです。Google ADKのフレームワークに基づき、エージェントをその特性（自律性、手順性、推論能力）に応じて **LlmAgent**, **WorkflowAgent**, **BaseAgent** に分類・実装し、オーケストレーターがこれらを統括します。

## 2. エージェント構成図

| エージェント名 | ADK分類 | 役割 | 主な責務 |
| :--- | :--- | :--- | :--- |
| **1. 管理 (Manager)** | `LlmAgent` | 司令塔 | ユーザー対話、フェーズ管理 (Routing) |
| **2. 監視 (Observer)** | `BaseAgent` | 自律監視 | 定点観測、データ蓄積、環境地図作成 |
| **3. 探索 (Explorer)** | `WorkflowAgent` | 実地探索 | DB検索、物理デバイス操作、高速探索ループ |
| **4. 推論 (Detective)** | `LlmAgent` | 高度推論 | 時系列分析、アブダクション (仮説形成) |

## 3. エージェント詳細仕様

### 3.1. 管理エージェント (Manager / Orchestrator)
*   **分類**: `LlmAgent`
*   **概要**: ユーザーとの唯一のインターフェース。会話の文脈を理解し、適切なサブエージェント（ツール）へタスクを振り分ける。
*   **判断ロジック (Routing)**:
    1.  **Phase 1 (記憶照会)**: まず **探索エージェント** に「記憶（DB）」を確認させる。
    2.  **Phase 2 (物理探索)**: 記憶になければ、**探索エージェント** に「実地探索」を指示する。
    3.  **Phase 3 (高度推論)**: それでも発見できない場合、**推論エージェント** にハンドオフ（移譲）する。

### 3.2. 監視エージェント (Observer)
*   **分類**: `BaseAgent`
*   **概要**: ユーザーの介在なしにバックグラウンドで自律的に稼働し、コンテキスト（世界モデル）を構築する。
*   **トリガー**:
    *   **動体検知**: ブラウザ側での画像処理（グレースケール化・ピクセル一致率判定）で変化があった場合のみクラウドへ送信。
    *   **定期実行**: 1時間に1回、または無人判定時。
*   **主要機能**:
    *   **メタデータ生成**: 取得画像に対して Gemini Flash 等を使用し、物体検知・要約を行い Firestore へ保存。
    *   **定期スキャン (Mapping)**: 360度回転し、最新の死角なしマップを作成。
    *   **コンテキスト理解 (壁判定)**: 回転中に「壁」や「障害物」で視界ゼロの角度を特定。次回のスキャンから当該角度を除外し、リソースを最適化する。

### 3.3. 探索エージェント (Explorer)
*   **分類**: `WorkflowAgent`
*   **概要**: 確立された手順（SOP）に従い、最短経路で探索を実行する。LLMの推論による迷いを排除し、速度を優先する。
*   **実行ワークフロー**:
    1.  **簡易推論 (Memory Check)**:
        *   Firestore の `detection_logs` を検索。対象物体の最終目撃情報（角度・時刻）を取得。
    2.  **デバイス操作 (Positioning)**:
        *   特定された角度（例: 45度）へ Obniz を急速旋回させる。
    3.  **ローカル高速探索 (Local Loop)**:
        *   クラウドを経由せず、ローカルデバイス（ブラウザ）へ探索モードへの移行指令を出す。
        *   ブラウザ側で Obniz操作 <-> 物体認識 の高速ループを実行し、対象物を特定する。
    4.  **結果報告**:
        *   発見の可否を Manager へ返す。

### 3.4. 推論エージェント (Detective)
*   **分類**: `LlmAgent` (Sub-Agent)
*   **概要**: 物理探索で解決しなかった難問に対し、論理的な飛躍（推論）を用いて解を導く。
*   **起動条件**: 探索エージェントが「降参（Not Found）」を返した場合。
*   **推論プロセス (Abduction)**:
    *   **時系列検索**: Firestore から対象単語（例: "remote"）に関連する過去ログを時系列で取得。
    *   **消失点分析**: 物体が消えた瞬間（Before/After）の画像を Storage から取得し比較。
    *   **仮説生成**: 「14:00にカバンに入れる動作が確認できるため、現在は部屋（物理空間）ではなくカバンの中（不可視領域）にある」といった回答を生成する。

## 4. データ構造設計 (Firestore Schema)
監視エージェントが書き込み、探索・推論エージェントが読み込む共通言語としてのデータスキーマです。

### Collection: `detection_logs`

```json
{
  // ▼ 基本情報 (Indexing: timestamp DESC)
  "doc_id": "log_20260125_100005",
  "timestamp": "2026-01-25T10:00:05Z",
  "image_storage_path": "gs://janus-logs/2026/01/25/img_100005.jpg",

  // ▼ 空間コンテキスト (Obniz制御・壁判定用)
  "motor_angle": 45,            // カメラの絶対角度 (0-360)
  "scan_session_id": "scan_A",  // 定期スキャンのグループID (単発検知ならnull)
  "is_blind_spot": false,       // 壁などで視界が悪い場合は true (次回スキップ用)

  // ▼ 環境情報 (推論Agentの「見えない理由」判断用)
  "environment": {
    "trigger": "motion",        // motion(動体) / periodic(定期) / manual(手動)
    "brightness_score": 0.8,    // 0.0(暗黒) ~ 1.0(明瞭)
    "scene_description": "A remote control on a wooden table." // Gemini Flashによる要約
  },

  // ▼ 検出物体詳細 (探索Agentの「当たり」付け用)
  "detected_objects": [
    {
      "label": "remote",
      "confidence": 0.98,
      "bounding_box": {         // 画面内の位置
        "x": 0.5, "y": 0.6,
        "w": 0.1, "h": 0.05
      },
      "occupancy_ratio": 0.005, // 画面占有率 (距離推定: 小さい=遠い)
      "state_change": "moved"   // 前回位置と比較して移動していればタグ付け
    }
  ]
}
```

## 5. 技術スタックによる実装マッピング

| コンポーネント | 技術要素 | 実装上のポイント |
| :--- | :--- | :--- |
| **Agent Framework** | Google Cloud ADK | `LlmAgent`, `WorkflowAgent`, `BaseAgent` のクラス継承を利用 |
| **Brain (LLM)** | Gemini 1.5 Pro/Flash | Manager/Detectiveには Pro、Observerの要約には Flash を利用 |
| **Database** | Firestore | ベクトル検索ではなく、構造化データのクエリを主軸にする（確実性重視） |
| **Device Control** | Obniz Cloud API | REST API経由で操作、またはブラウザJS SDKからの直接制御 |
| **Vision (Edge)** | OpenCV.js / TF.js | ブラウザ側での「動体検知」と「高速探索ループ」に使用 |

## 6. 実装ディレクトリ構成

Google ADK を利用した推奨ディレクトリ構成は以下の通りです。責務ごとにディレクトリを分離し、プロンプトやツール定義をモジュール化します。

```text
backend/
├── agents/                 # ADKのエージェントクラス継承実装
│   ├── orchestrator.py     # Manager (LlmAgent)
│   ├── observer.py         # Observer (BaseAgent)
│   ├── explorer.py         # Explorer (WorkflowAgent)
│   └── detective.py        # Detective (LlmAgent)
├── tools/                  # 各エージェントが使用するTool定義
│   ├── search_db.py        # Firestore検索ツール
│   ├── move_camera.py      # Obniz制御ツール
│   └── vision_analysis.py  # 画像解析ツール
├── prompts/                # LLMへのインストラクション (YAML/Text)
│   ├── orchestrator.yaml   # 意図分類・ルーティング用プロンプト
│   └── detective_abduction.yaml # 推論用プロンプト
├── models/                 # データモデル (Pydantic)
│   ├── analysis_result.py  # 共通レスポンス型
│   └── log_entry.py        # Firestoreドキュメント型
├── utils/                  # ユーティリティ
│   └── firebase.py         # DB/Storage接続ヘルパー
└── main.py                 # FastAPI エントリーポイント
```

### 実装のポイント
1.  **プロンプトの外部化 (`/prompts`)**:
    *   `LlmAgent` の `instruction` 引数に渡すテキストは、Pythonコード内に埋め込まず、`prompts/` 以下のYAMLやテキストファイルで管理します。これにより、プロンプトエンジニアリングとロジック実装を分離できます。

2.  **ツールのモジュール化 (`/tools`)**:
    *   エージェントが使用する機能（関数）は `tools/` に定義し、`LlmAgent(tools=[...])` のように注入します。

3.  **ADKの活用**:
    *   各エージェントは `google.adk.agents` パッケージの `LlmAgent`, `WorkflowAgent`, `BaseAgent` を適切に継承して実装します。
