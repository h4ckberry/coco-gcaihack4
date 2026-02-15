# 【COCO】「ドコ？のヒントはココにある」お部屋の探し物AIパートナー

<div align="center">
  <img src="https://storage.googleapis.com/zenn-user-upload/8a854f61630e-20260215.png" alt="CoCo Concept Art" width="600">
</div>

<br>

[![Youtube Demo](https://img.youtube.com/vi/qLOZCnXTWzc/0.jpg)](https://youtu.be/qLOZCnXTWzc)

---

## 概要

**「あれ、どこに置いたっけ？」**

CoCoは、そんな日常のふとした瞬間に訪れる「探し物」のストレスからあなたを解放する、**Agentic AI パートナー**です。
部屋に設置したデバイス（プロトタイプ：iPhone 16 + obniz）が、あなたの代わりに部屋の様子を優しく「見守り」、モノの場所を記憶します。

「監視」ではなく「見守り」をテーマに、生活に溶け込む温かみのあるデザインと、能動的に提案を行うAgenticな振る舞いを特徴としています。

### 主な機能

1.  **「あれどこ？」に答える**: 自然言語で「スマホどこ？」と聞くと、部屋の映像ログから場所を特定し、「ソファの上です」と教えてくれます。
2.  **文脈からの推論**: 映像に見つからない場合でも、Googleカレンダー等の外部ツールと連携し「ジムに行っていたなら、バッグの中かも？」と推論・提案します。
3.  **自律的な物理探索**: 死角がある場合、obnizと連携してカメラの向きを変え、自ら探しに行きます。

## 技術的特徴

本プロダクトは、デジタル領域（ソフトウェア）と物理領域（IoTデバイス）をシームレスに接続するため、Google Cloud のモダンなサーバーレス構成をフル活用しています。

![Architecture Diagram](https://storage.googleapis.com/zenn-user-upload/aee668f0f9d4-20260215.png)

- **AI Engine**: Azure Vertex AI Agent Engine (Backend)
- **Frontend**: Next.js + Firebase Hosting
- **IoT**: obniz + SG90 Servo
- **Development**: AI-Driven Development with "Antigravity"

## 起動方法

本アプリケーションはモノレポ構成を採用しています。

### 1. 環境変数の設定

`src/backend/` および `src/frontend/` に `.env` ファイルを作成し、必要なAPIキーを設定してください。

**Backend (.env)**
```env
GEMINI_API_KEY="YOUR_API_KEY"
GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
```

**Frontend (.env)**
```env
NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
```

### 2. フロントエンドの起動

```bash
cd src/frontend/
npm install
npm run dev
```

### 3. バックエンドの起動

```bash
cd src/backend/
pip install -r requirements.txt
```

## AI Coding & Development

本プロジェクトは **Antigravity** を活用した AI-Driven Development で開発されました。
仕様策定から実装、コミットまでをAIエージェントと協働で行い、**Blender MCP** を用いた自然言語による3Dモデル生成など、開発プロセス自体も「Agentic」であることをテーマにしています。

---

> [!NOTE]
> このリポジトリは 第4回 Agentic AI Hackathon with Google Cloud 提出作品です。
> 詳細な解説記事: [Zenn Link](https://zenn.dev/...)
