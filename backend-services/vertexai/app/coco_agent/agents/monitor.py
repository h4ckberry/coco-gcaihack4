from typing import Dict, Any, List, Optional
import json
import os
import logging
import asyncio
from google.adk.agents import Agent
from app.coco_agent.prompts.loader import load_prompt
from app.coco_agent.tools.storage_tools import get_image_uri_from_storage
from app.coco_agent.tools.firestore_tools import save_monitoring_log
from app.services.monitoring_service import get_monitoring_service
from app.app_utils.obniz import ObnizController
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def suspend_monitoring(reason: str = "explorer_request", duration: int = 300) -> str:
    """
    監視ループを一時停止します。Explorer Agent がカメラを操作する前に呼び出してください。

    Args:
        reason: 一時停止の理由（例: "explorer_request", "user_request"）
        duration: 一時停止の最大期間（秒）。この期間が過ぎると自動的に再開されます。

    Returns:
        一時停止の結果メッセージ。
    """
    service = get_monitoring_service()
    result = service.suspend(reason=reason, duration=duration)
    return json.dumps(result, ensure_ascii=False)


def resume_monitoring() -> str:
    """
    一時停止中の監視ループを再開します。Explorer Agent の操作が完了した後に呼び出してください。

    Returns:
        再開の結果メッセージ。
    """
    service = get_monitoring_service()
    result = service.resume()
    return json.dumps(result, ensure_ascii=False)


def get_monitoring_status() -> str:
    """
    現在の監視ステータスを取得します（一時停止中か、誰が停止したか等）。

    Returns:
        監視ステータスの JSON 文字列。
    """
    service = get_monitoring_service()
    result = service.get_status()
    return json.dumps(result, ensure_ascii=False)


monitor_agent = Agent(
    name="monitor_agent",
    model="gemini-2.5-flash",
    description="固定画角のカメラ画像を継続的に分析し、物体検出結果をFirestoreにログする監視Agent。suspend/resumeによる排他制御をサポート。",
    instruction=load_prompt("monitor"),
    tools=[
        detect_objects,
        rotate_and_capture,
        suspend_monitoring,
        resume_monitoring,
        get_monitoring_status,
        get_image_uri_from_storage, 
        save_monitoring_log
    ],
)

# Initialize Gemini Client
# We use google-genai library as per existing imports
try:
    client = genai.Client(location=os.environ.get("GOOGLE_CLOUD_LOCATION"))
except Exception as e:
    logger.warning(f"GenAI Client initialization failed: {e}")
    client = None

def rotate_and_capture(angle: int) -> str:
    """
    Rotates the camera to the specified angle.
    Returns a status message.
    """
    # Activity update
    get_monitoring_service().update_activity()
    
    obniz.rotate(angle)
    return f"Camera rotated to {angle} degrees."

def detect_objects(query: str = "detect everything", image_uri: Optional[str] = None) -> str:
    """
    Analyzes the camera image to detect objects based on a query.
    
    Args:
        query: The user's question or "detect everything" to list all objects.
        image_uri: Optional GS URI of the image to analyze. If not provided, the latest image is fetched.
        
    Returns:
        A text summary of what was found.
    """
    # Activity update
    get_monitoring_service().update_activity()

    if not client:
        return "Error: GenAI client not initialized."

    # 1. Get Image
    if not image_uri:
        # Fetch the latest image URI if not provided
        # We use a tool from storage_tools to get the latest uploaded image
        # For this implementation, we assume get_image_uri_from_storage returns the latest "gs://" URI
        # Note: In a real flow, the agent might need to capture -> upload -> get URI.
        # Here we assume an image is ready or we just get the 'latest'.
        image_uri = get_image_uri_from_storage()
    
    if not image_uri:
        return "Error: No image available to analyze."

    # 2. Construct Prompt based on Query Type
    is_generic = query.lower().strip().strip(".,!?") in [
        "detect everything", "what is in this image?", "describe the main objects in this scene briefly",
        "monitor", "check", "scan"
    ]

    base_schema = """
    Output JSON:
    {
        "found": boolean,
        "box_2d": [ymin, xmin, ymax, xmax] or null (for the target object),
        "label": "target object name" or "Multiple Objects" if generic,
        "all_objects": [ 
            { 
                "box_2d": [ymin, xmin, ymax, xmax], 
                "label": "object name",
                "confidence": float (0.0-1.0)
            },
            ...
        ],
        "environment": {
            "scene_description": "A concise description of the scene context (e.g., 'Indoor messy desk', 'Bright living room')",
            "brightness_score": int (1-5, where 5 is very bright),
            "trigger": "manual_query"
        }
    }
    """

    if is_generic:
        prompt_text = f"""
        Analyze the image and detect ALL visible objects.
        List every distinct object you see with its bounding box and confidence.
        Also analyze the environment details.
        
        {base_schema}
        """
    else:
        prompt_text = f"""
        Analyze the image and find the object: "{query}".
        Also detect ALL other visible objects in the scene.
        
        {base_schema}
        """

    try:
        # 3. Call Generative Model
        # Using gemini-3-flash-preview as requested
        model_name = "gemini-3-flash-preview"
        
        # Load image part
        # google-genai supports gs:// URIs directly in Part.from_uri logic usually, 
        # or we might need to verify if we need to download it.
        # Assuming Vertex AI / Gemini API handles gs:// URIs if in same project/location.
        if image_uri.startswith("gs://"):
             image_part = types.Part.from_uri(file_uri=image_uri, mime_type="image/jpeg")
        else:
             # Fallback or error if not gs://
             pass 

        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(prompt_text),
                        image_part
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.5
            )
        )
        
        # 4. Parse Response
        text_resp = response.text.strip()
        # Clean up code blocks if standard text response
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
        
        data = json.loads(text_resp)
        
        # 5. Save to Firestore
        env_data = data.get("environment", {})
        # Ensure trigger is set properly if missing
        if "trigger" not in env_data:
            env_data["trigger"] = "query" if not is_generic else "monitor"

        save_monitoring_log(
            image_storage_path=image_uri,
            detected_objects=data.get("all_objects", []),
            environment=env_data,
            motor_angle=obniz.current_angle if hasattr(obniz, "current_angle") else 0,
            scan_session_id=None # Single shot query
        )
        
        # 6. Return Summary
        found = data.get("found", False)
        main_label = data.get("label", "Unknown")
        
        if is_generic:
            return f"Monitoring Report: Detected {len(data.get('all_objects', []))} objects. Scene: {env_data.get('scene_description', 'No description')}."
        else:
            if found:
                return f"Found '{main_label}'. (Confidence: High)" # JSON usually has list, but 'found' flag confirms it.
            else:
                return f"Could not find '{query}' in the current view."

    except Exception as e:
        logger.error(f"Detection failed: {e}")
        return f"Error observing scene: {str(e)}"

# Setup Monitoring Service Callbacks
def _scan_callback_wrapper(angle: int):
    """Wrapper for scan callback to match signature and pre-fill query."""
    # Note: detect_objects is sync, which is fine as service calls it directly.
    # We might want to pass 'monitor' as query.
    logger.info(f"Auto-scan triggered at angle {angle}")
    detect_objects(query="monitor")

def _rotate_callback_wrapper(angle: int):
    obniz.rotate(angle)

# Initialize and Start Service
service = get_monitoring_service()
service.set_callbacks(_scan_callback_wrapper, _rotate_callback_wrapper)
# Note: start() is async. In a real app, this should be awaited in the startup lifecycle.
# Since this is a module level usage, we rely on the app runner to handle loop or we fire and forget?
# ADK agents don't have a 'startup' hook easily accessible here without App wrapper modification.
# However, for this hackathon context, we can try to schedule it if there is a running loop, or assume called externally.
# Better: We just expose the service and let the App (agent_monitor.py or agent_engine_app.py) start it.
# Let's try to grab the current loop if available?
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(service.start())
except Exception:
    pass # Loop might not be started yet

def suspend_monitoring(reason: str = "explorer_request", duration: int = 300) -> str:
    """
    監視ループを一時停止します。Explorer Agent がカメラを操作する前に呼び出してください。

    Args:
        reason: 一時停止の理由（例: "explorer_request", "user_request"）
        duration: 一時停止の最大期間（秒）。この期間が過ぎると自動的に再開されます。

    Returns:
        一時停止の結果メッセージ。
    """
    service = get_monitoring_service()
    result = service.suspend(reason=reason, duration=duration)
    return json.dumps(result, ensure_ascii=False)


def resume_monitoring() -> str:
    """
    一時停止中の監視ループを再開します。Explorer Agent の操作が完了した後に呼び出してください。

    Returns:
        再開の結果メッセージ。
    """
    service = get_monitoring_service()
    result = service.resume()
    return json.dumps(result, ensure_ascii=False)


def get_monitoring_status() -> str:
    """
    現在の監視ステータスを取得します（一時停止中か、誰が停止したか等）。

    Returns:
        監視ステータスの JSON 文字列。
    """
    service = get_monitoring_service()
    result = service.get_status()
    return json.dumps(result, ensure_ascii=False)

monitor_agent = Agent(
    name="monitor_agent",
    model="gemini-2.5-flash", 
    description="固定画角のカメラ画像を継続的に分析し、物体検出結果をFirestoreにログする監視Agent。suspend/resumeによる排他制御をサポート。",
    instruction=load_prompt("monitor"),
    tools=[
        detect_objects,
        rotate_and_capture,
        suspend_monitoring,
        resume_monitoring,
        get_monitoring_status,
        get_image_uri_from_storage, 
        save_monitoring_log
    ]

)
