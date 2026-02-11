from typing import Dict, Any, List, Optional
import json
import os
import logging
import asyncio
from google.adk.agents import Agent
from app.coco_agent.prompts.loader import load_prompt
from app.coco_agent.tools.storage_tools import get_image_uri_from_storage, get_latest_image_uri
from app.coco_agent.tools.firestore_tools import save_monitoring_log
from app.services.monitoring_service import get_monitoring_service
from app.app_utils.obniz import ObnizController
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

obniz_controller = ObnizController()

_BASE_SCHEMA = """
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




# Global GenAI Client Cache
_genai_client = None

def get_genai_client():
    """
    Returns the GenAI client, initializing it with API key or ADC as appropriate.
    """
    global _genai_client
    if _genai_client is None:
        try:
            from google import genai
            
            api_key = os.environ.get("GOOGLE_API_KEY")
            use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "1") == "1"
            
            if api_key and not use_vertex:
                # Force AI Studio mode by temporarily unsetting Vertex env vars
                # The google-genai library defaults to Vertex if these are present
                # Use a local dict to avoid modifying global os.environ permanently here if possible, 
                # but Client initialization might look at os.environ directly.
                # So we use the 'unset' trick inside a lock or just rely on it.
                
                # Check for explicit base_url or just rely on library behavior if Vertex envs are gone
                _genai_client = genai.Client(
                    api_key=api_key, 
                    http_options={'api_version': 'v1beta'}
                )
                logger.info("GenAI client initialized with API Key (Forced AI Studio mode)")
            else:
                # Use default (Vertex AI mode)
                _genai_client = genai.Client(
                    location=os.environ.get("GOOGLE_CLOUD_LOCATION"),
                    project=os.environ.get("GOOGLE_CLOUD_PROJECT")
                )
                logger.info("GenAI client initialized with Vertex AI mode")
        except Exception as e:
            logger.warning(f"GenAI Client initialization failed: {e}")
            _genai_client = None
    return _genai_client
    
def rotate_and_capture(angle: int) -> str:
    """
    Rotates the camera to the specified angle.
    Returns a status message.
    """
    # Activity update
    get_monitoring_service().update_activity()

    obniz_controller.rotate(angle)
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

    # 1. Get Image
    # 1. Get Image
    if not image_uri:
        # Fetch the latest image URI if not provided
        # We use a tool from storage_tools to get the latest uploaded image
        # Note: This fetches the actual latest file from GCS.
        image_uri = get_latest_image_uri()

    if not image_uri:
        return "Error: No image available to analyze (Bucket empty or access failed)."

    # 2. Construct Prompt based on Query Type
    is_generic = query.lower().strip().strip(".,!?") in [
        "detect everything", "what is in this image?", "describe the main objects in this scene briefly",
        "monitor", "check", "scan"
    ]

    base_schema = _BASE_SCHEMA

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
        # 3. Call Generative Model
        client = get_genai_client()
        if not client:
             return "Error: GenAI client not initialized (Auth error)."

        # Using gemini-3-flash-preview as requested by user
        model_name = "gemini-3-flash-preview"

        # Load image part
        # 3. Handle Image Part
        # AI Studio mode (GOOGLE_GENAI_USE_VERTEXAI="0") does NOT support gs:// URIs directly.
        # We need to download it if in AI Studio mode.
        use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "1") == "1"
        if image_uri.startswith("gs://"):
            if use_vertex:
                # Vertex AI supports gs:// URIs
                image_part = types.Part.from_uri(file_uri=image_uri, mime_type="image/jpeg")
            else:
                # AI Studio mode requires bytes or upload. Let's try to download.
                logger.info(f"AI Studio mode detected. Attempting to download {image_uri} for analysis...")
                
                # Helper to get image bytes
                image_bytes = None
                download_error = None

                # 1. Try Authenticated GCS Client
                try:
                    from app.coco_agent.tools.storage_tools import get_storage_client
                    storage_client = get_storage_client()
                    
                    if storage_client:
                        # Parse gs:// URI
                        path_parts = image_uri.replace("gs://", "").split("/", 1)
                        if len(path_parts) >= 2:
                            bucket_name, blob_name = path_parts
                            bucket = storage_client.bucket(bucket_name)
                            blob = bucket.blob(blob_name)
                            image_bytes = blob.download_as_bytes()
                            logger.info(f"Successfully downloaded via GCS Client: {image_uri}")
                except Exception as e:
                    download_error = e
                    logger.warning(f"GCS Client download failed (trying fallback): {e}")

                # 2. Fallback: Try Public/Signed URL via HTTP
                if image_bytes is None:
                    try:
                        import requests
                        # Construct public URL: https://storage.googleapis.com/BUCKET_NAME/BLOB_NAME
                        path_parts = image_uri.replace("gs://", "").split("/", 1)
                        if len(path_parts) >= 2:
                            bucket_name, blob_name = path_parts
                            # Note: This only works if object is public
                            public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
                            logger.info(f"Attempting download via Public URL: {public_url}")
                            
                            resp = requests.get(public_url, timeout=10)
                            if resp.status_code == 200:
                                image_bytes = resp.content
                                logger.info(f"Successfully downloaded via Public URL: {public_url}")
                            else:
                                logger.warning(f"Public URL download failed: {resp.status_code}")
                    except Exception as e:
                        logger.warning(f"Public URL download check failed: {e}")

                if image_bytes:
                    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                else:
                    return f"Error: Failed to fetch image from GCS. Auth failed and public access denied. ({download_error})"
        else:
             logger.error(f"Unsupported image URI format: {image_uri}")
             return f"Error: Unsupported image URI format: {image_uri}"

        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt_text),
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
            motor_angle=obniz_controller.current_angle if hasattr(obniz_controller, "current_angle") else 0,
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
    obniz_controller.rotate(angle)

# Initialize and Start Service
service = get_monitoring_service()
service.set_callbacks(_scan_callback_wrapper, _rotate_callback_wrapper)
# Note: start() is async. In a real app, this should be awaited in the startup lifecycle.
# Since this is a module level usage, we rely on the app runner to handle loop or we fire and forget?
# ADK agents don't have a 'startup' hook easily accessible here without App wrapper modification.
# However, for this hackathon context, we can try to schedule it if there is a running loop, or assume called externally.
# Better: We just expose the service and let the App (agent_monitor.py or agent_engine_app.py) start it.
# Let's try to grab the current loop if available?




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
