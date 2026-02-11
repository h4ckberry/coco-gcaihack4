import os
import sys
import shutil
import subprocess

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
    print("❌ Error: PROJECT_ID is not set.")
    sys.exit(1)

def generate_and_move_requirements():
    print("📦 Generating requirements.txt...")
    req_file_root = "requirements.txt"
    req_file_app = "app/requirements.txt" # ★ここがポイント！appの中に置く

    try:
        # 1. uv で requirements.txt を生成
        subprocess.check_call([
            "uv", "export", "--format", "requirements-txt", "--no-hashes", "--output-file", req_file_root, "--quiet"
        ])

        # 2. クリーニング (-e . などを削除)
        with open(req_file_root, "r") as f:
            lines = f.readlines()

        # google-cloud-aiplatform が入っているか確認（なければ強制追加）
        has_vertex = any("google-cloud-aiplatform" in l for l in lines)
        cleaned_lines = [l for l in lines if not l.strip().startswith("-e") and "file://" not in l]

        if not has_vertex:
            print("⚠️ google-cloud-aiplatform missing, adding manually...")
            cleaned_lines.append("google-cloud-aiplatform\n")

        # 3. appフォルダの中に保存（これでアップロード対象になる）
        with open(req_file_app, "w") as f:
            f.writelines(cleaned_lines)

        print(f"✅ Requirements file placed at: {req_file_app}")
        return req_file_app

    except Exception as e:
        print(f"❌ Failed to generate requirements.txt: {e}")
        sys.exit(1)

def deploy_agent(display_name, entrypoint_object="agent_engine"):
    print(f"\n🚀 Starting deployment for [{display_name}]...")

    # requirements.txt を app/ の中に準備
    req_file_path = generate_and_move_requirements()

    entrypoint_module = "app.agent_orchestrator"
    if "Monitor" in display_name:
         entrypoint_module = "app.agent_monitor"

    env_keys = ["PROJECT_ID", "GCLOUD_PROJECT_ID", "GCLOUD_LOCATION", "FIREBASE_STORAGE_BUCKET", "GOOGLE_GENAI_USE_VERTEXAI"]

    if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI"): os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
    env_vars_arg = ",".join([f"{k}={os.getenv(k)}" for k in env_keys if os.getenv(k)])

    cmd = [
        sys.executable, "-m", "app.app_utils.deploy",
        "--project", PROJECT_ID,
        "--location", LOCATION,
        "--display-name", display_name,
        "--source-packages", "./app",      # appフォルダごとアップロード（中にrequirements.txtがある）
        "--entrypoint-module", entrypoint_module,
        "--entrypoint-object", entrypoint_object,
        "--requirements-file", req_file_path, # app/requirements.txt を指定
        "--max-instances", "3",
    ]

    if env_vars_arg:
        cmd.extend(["--set-env-vars", env_vars_arg])

    print(f"Running command: {' '.join(cmd)}")

    env = os.environ.copy()
    env["PYTHONPATH"] = f".:{env.get('PYTHONPATH', '')}"

    result = subprocess.run(cmd, env=env)

    if result.returncode != 0:
        print(f"❌ Deployment failed for {display_name}")
        sys.exit(result.returncode)
    else:
        print(f"✅ Deployment successful for {display_name}")

if __name__ == "__main__":
    # Orchestrator
    deploy_agent(
        display_name="Orchestrator Agent V2",
        entrypoint_object="agent_engine"
    )

    # Monitor
    deploy_agent(
        display_name="Monitor Agent",
        entrypoint_object="agent_engine"
    )
