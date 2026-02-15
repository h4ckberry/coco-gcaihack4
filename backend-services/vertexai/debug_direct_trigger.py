
import asyncio
import os
import logging
from dotenv import load_dotenv

# Load envs
load_dotenv()
load_dotenv("app/.env")

# Force Vertex AI mode for this test to match deployment
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.coco_agent.agents.monitor import monitor_agent
from app.coco_agent.tools.storage_tools import get_latest_image_uri
from google.adk.runners import InMemoryRunner
from google.genai import types

# Override GOOGLE_APPLICATION_CREDENTIALS to absolute path for this script
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("app/credentials.json")
# Force us-west1 as it might be where the quota is
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-west1"

async def main():
    print("--- Starting Direct API Trigger Verification ---")

    # 1. Get Latest Image URI to simulate frontend upload
    print("1. Fetching latest image URI...")
    latest_uri = get_latest_image_uri()
    if not latest_uri:
        print("[ERROR] Could not fetch latest image URI. Check GCS credentials or bucket content.")
        return
    print(f"[OK] Found latest image: {latest_uri}")

    # 2. Initialize Runner
    print("2. Initializing Agent Runner...")
    from google.adk.apps import App
    app_wrapper = App(root_agent=monitor_agent, name="monitor_app")
    runner = InMemoryRunner(app=app_wrapper)
    
    session = await runner.session_service.create_session(
        session_id="debug-direct-trigger",
        user_id="debug-user",
        app_name="monitor_app"
    )

    # 4. Simulate User Prompt (Direct API Call)
    prompt_text = f"Analyze this image: {latest_uri}"
    print(f"3. Sending Prompt: '{prompt_text}'")

    # 5. Run Agent
    try:
        response_text = ""
        async for event in runner.run_async(
            session_id=session.id,
            user_id="debug-user",
            new_message=types.Content(parts=[types.Part(text=prompt_text)])
        ):
            # Capture text output
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
                        print(part.text, end="", flush=True)
        print("\n")
        
        if "Found" in response_text or "Monitoring Report" in response_text or "Could not find" in response_text:
             print("[OK] Verification Successful: Agent processed the image URI.")
        else:
             print("[WARN] Verification Warning: Agent response was unexpected. Check logs.")

    except Exception as e:
        print(f"[ERROR] Error during agent execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())
