# CoCo - 『あれ、どこいった？』を解決し、ゆとりある時間を創る。優しく見守るお部屋のAIパートナー

<!-- 必要に応じてバッジを追加してください -->
<!-- [![Build](https://github.com/your-org/coco/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/coco/actions/workflows/ci.yml) -->

[![Youtubeへのリンク](docs/thumbnail.png)](https://youtu.be/DUMMY_LINK)
(クリックすると YouTube の紹介動画に飛びます - ※プレースホルダー)

## 概要

**「あれ、どこに置いたっけ？」**

CoCoは、そんな日常のふとした瞬間に訪れる「探し物」のストレスからあなたを解放する、Agentic AI アプリケーションです。
部屋に設置したデバイス（プロトタイプ：iPhone 16）が、あなたの代わりに部屋の様子を優しく「見守り」、モノの場所を記憶します。

「監視」ではなく「見守り」をテーマに、ユーザーに安心感を与える温かみのあるUIと、親しみやすいキャラクターとの対話を通じて、あなたの生活をサポートします。

- **解決する課題:** 部屋の中でモノをなくし、探すために費やす「無駄な時間」と「ストレス」
- **コア機能:** 自然言語による探し物の問い合わせ（「リモコンどこ？」→「さっきあそこで使ってましたよ」）

## ターゲット・コンセプト

- **ペルソナ:** 都内IT企業勤務の30代男性（サトシ）。ガジェット好きだが片付けが苦手で、朝の探し物にストレスを感じている。
- **デザイン哲学:**
  - **Not Surveillance, But Watching Over:** 監視カメラの冷徹さを排除し、暖色系や丸みのあるデザインで「見守られている」安心感を醸成。
  - **Reliable yet Charming:** 完璧すぎるAIではなく、少し愛嬌のある「相棒」のような存在（ベイマックスやカービィのようなイメージ）。

## 全体構成

本アプリケーションはモノレポ構成を採用しています。

<!-- 構成図の画像を配置してください -->
![構成図](./docs/architecture.png)

## 起動方法

本アプリケーションの開発には Node.js (Frontend) と Python (Backend) が必要です。

### 環境変数の設定

初回起動時、フロントエンドとバックエンドで環境変数を設定する必要があります。

- `src/backend/`フォルダー内に `.env` ファイルを作成し、以下の内容を記述してください:

```txt
# Gemini APIキー
GEMINI_API_KEY="あなたのGemini APIキー"

# その他の必要な環境変数
# ...
```

- `src/frontend/`フォルダー内に `.env` ファイルを作成し、以下の内容を記述してください:

```txt
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### フロントエンドの起動

```sh
cd src/frontend/
npm install
npm run dev
```

### バックエンドの起動

※以下は構成例です。プロジェクトの実際のパッケージマネージャーに合わせて調整してください（例: uv, poetry, pip）。

```sh
cd src/backend/
# 依存関係のインストール
pip install -r requirements.txt 
# または uv sync など

# サーバーの起動
uv run uvicorn main:app --reload
```

## AI Coding

Cline、Github Copilot などを利用して開発することを想定しており、Agent が E2E で修正をしやすいように、本リポジトリはモノレポ構成になっています。

インストラクションは[AGENTS.md](AGENTS.md)を用いて管理しており、`.clinerules`はルートの`AGENTS.md`へのシンボリックリンクとなっています（※環境に合わせて設定してください）。

インストラクションを修正する場合は、`AGENTS.md`を修正してください。

> [!IMPORTANT]
> インストラクションを更新するときは、`AGENTS.md`を更新してください。
