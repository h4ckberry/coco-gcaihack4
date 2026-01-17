# COCO - [アプリの簡単な説明]

[![Build](https://github.com/USER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/ci.yml)
[![Deploy Frontend](https://github.com/USER/REPO/actions/workflows/firebase-hosting-merge.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/firebase-hosting-merge.yml)

[![Youtubeへのリンク](docs/thumbnail.png)](https://youtu.be/VIDEO_ID)
(クリックすると YouTube の紹介動画に飛びます)

## 概要

- [記事へのリンク - Zenn](https://zenn.dev/)
- [デモサイト](https://example.web.app/)
- [API Docs](https://api-service-url/docs)

## 全体構成

本アプリケーションは GCP 上にデプロイされており、xxx

![構成図](./docs/architecture.png)

## 起動方法

本アプリケーションの開発には Node.js (v20-24) と Python (>=3.11) が必要です。

### 環境変数の設定

初回起動時、xxx

### フロントエンドの起動

```sh
cd src/frontend/

```

### バックエンドの起動

```sh
cd src/backend/

```

### ダミーデータの挿入

DBデータをリセットしてダミーデータを挿入する場合は、以下のコマンドを実行してください。

```sh
cd src/backend/
uv run python scripts/seed.py
```

#### Docker で API サーバをビルド・実行する

Cloud Run で実行する場合は Docker を利用します。ローカルで Docker イメージをビルドして実行するには以下のコマンドを使用します。

```sh
cd src/backend
docker build -t coco_api .
docker run --rm -p 8000:8000 coco_api
```

## AI Coding

Cline、Github Copilot、Codex、Gemini Code Assist を利用して開発することを想定しており、Agent が E2E で修正をしやすいように、本リポジトリはモノレポ構成になっています。

インストラクションは[AGENTS.md](AGENTS.md)を用いて管理しており、`.clinerules`は各フォルダの`AGENTS.md`へのシンボリックリンクとなっています。

インストラクションを修正する場合は、各フォルダの`AGENTS.md`を修正してください。

> [!IMPORTANT]
> インストラクションを更新するときは、`AGENTS.md`を更新してください。
> `.clinerules/`は`AGENTS.md`に対するシンボリックリンクで同期されているため、直接更新しないでください。