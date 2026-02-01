import os
from vertexai.preview import reasoning_engines
from agent import root_agent

# 設定読み込み (GCLOUD_PROJECT_IDなどが必要な場合)
from settings import get_settings

def deploy():
    settings = get_settings()

    # requirements.txt から依存関係を読み込む
    with open("requirements.txt", "r") as f:
        reqs = [line.strip() for line in f if line.strip()]

    print("Deploying Agent to Vertex AI Agent Engine...")

    # Agent Engine アプリの作成 (デプロイ)
    # create() は内部でCloud Build等を動かし、Vertex AI上に推論エンジンを作成します
    remote_app = reasoning_engines.ReasoningEngine.create(
        reasoning_engine=root_agent,
        requirements=reqs,
        display_name="coco-sample-agent",
        description="Sample ADK Agent for CoCo",
        # sys_version="3.11", # 必要に応じてPythonバージョン指定
    )

    print(f"Deployment Complete!")
    print(f"Resource Name: {remote_app.resource_name}")
    print(f"Operation Name: {remote_app.operation_name}")

    return remote_app

if __name__ == "__main__":
    # 実行前に認証とプロジェクト設定が済んでいることを確認してください
    # gcloud auth application-default login
    # gcloud config set project YOUR_PROJECT_ID

    deploy()
