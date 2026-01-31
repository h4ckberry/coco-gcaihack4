import os
import sys
import shutil
import glob
import subprocess # Added for uv exportprocess

# .env loading
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv("app/.env")
except ImportError:
    pass

PROJECT_ID = os.getenv("GCLOUD_PROJECT_ID") or os.getenv("PROJECT_ID")
LOCATION = os.getenv("GCLOUD_LOCATION", "us-west1")

if not PROJECT_ID:
    print("❌ Error: PROJECT_ID is not set. Please check your .env file.")
    sys.exit(1)

def generate_requirements():
    """Generates a minimal requirements.txt manually to avoid conflict hell."""
    print("📦 Generating requirements.txt from uv lock...")
    req_file = "requirements.txt"

    try:
        # Use uv export to get the exact locked dependencies
        # --no-hashes is safer for cloud build compatibility
        subprocess.check_call([
            "uv", "export",
            "--format", "requirements-txt",
            "--no-hashes",
            "--output-file", req_file
        ])

        # Append uvicorn if missing/needed explicitly for some runtimes,
        # though usually it enters via dependencies.
        # Let's ensure google-cloud-aiplatform uses the right extra if not present.
        # But uv export should capture what's in pyproject.toml

        print("✅ Created exact requirements.txt from uv lock")
        return req_file
    except Exception as e:
        print(f"❌ Failed to generate requirements.txt: {e}")
        # Fallback or exit? Exit is safer to avoid deploying bad env.
        sys.exit(1)

def deploy_agent(display_name, entrypoint_module, entrypoint_object="agent_engine"):
    """
    Invokes app.app_utils.deploy to deploy the agent.
    """
    print(f"\n🚀 Starting deployment for [{display_name}]...")

    # .envの内容を --set-env-vars に変換するための準備
    # 重要な変数をピックアップして渡す
    env_keys = ["PROJECT_ID", "GCLOUD_PROJECT_ID", "GCLOUD_LOCATION", "FIREBASE_STORAGE_BUCKET"]
    env_vars_list = []
    for key in env_keys:
        val = os.getenv(key)
        if val:
            env_vars_list.append(f"{key}={val}")

    env_vars_arg = ",".join(env_vars_list)

    cmd = [
        sys.executable, "-m", "app.app_utils.deploy",
        "--project", PROJECT_ID,
        "--location", LOCATION,
        "--display-name", display_name,
        "--source-packages", "./app",
        "--entrypoint-module", entrypoint_module,
        "--entrypoint-object", entrypoint_object,
        "--requirements-file", "requirements.txt",
        "--max-instances", "3",
    ]

    if env_vars_arg:
        cmd.extend(["--set-env-vars", env_vars_arg])

    # コマンド実行
    cmd_str = " ".join(cmd)
    print(f"Running command: {cmd_str}")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"❌ Deployment failed for {display_name}")
        sys.exit(result.returncode)
    else:
        print(f"✅ Deployment successful for {display_name}")

if __name__ == "__main__":
    req_file = generate_requirements()

    try:
        # Orchestrator
        deploy_agent(
            display_name="Orchestrator Agent",
            entrypoint_module="app.agent_orchestrator"
        )

        # Monitor
        deploy_agent(
            display_name="Monitor Agent",
            entrypoint_module="app.agent_monitor"
        )

    finally:
        # Cleanup
        if os.path.exists(req_file):
            # デバッグのために残す設定なら残す
            # os.remove(req_file)
            pass
