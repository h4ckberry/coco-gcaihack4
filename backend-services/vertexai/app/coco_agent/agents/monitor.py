from typing import Dict, Any, List
import json
from google.adk.agents import Agent
from ..tools.storage_tools import get_image_uri_from_storage
from ..tools.firestore_tools import save_monitoring_log
from ...app_utils.obniz import ObnizController
from google.genai import types

# Initialize Obniz
obniz = ObnizController()

def rotate_and_capture(angle: int) -> str:
    """
    Rotates the camera to the specified angle.
    Returns a status message.
    """
    obniz.rotate(angle)
    return f"Camera rotated to {angle} degrees."

def detect_and_log(image_uri: str) -> Dict[str, Any]:
    """
    Analyzes the image at the given URI, detects objects, and logs to Firestore.
    Returns the detection result.
    """
    # This function is a bit complex for a simple tool call if we want to use the Agent's model inside it.
    # In ADK, tools are usually external functions.
    # However, the Agent itself has valid model access.
    # For simplicity, we will define this behavior in the Agent's instruction
    # and provide helper tools for the side effects (save_log).
    # But the Agent *is* the one doing detection.

    # We'll just return a dummy structure here if this was a tool,
    # but strictly speaking, the AGENT should do the "Thinking" (Detection).
    # So we will provide tools for:
    # 1. saving to DB
    # 2. controlling motor
    pass

monitor_agent = Agent(
    name="monitor_agent",
    model="gemini-2.5-flash",
    description="Agent for monitoring camera feeds, detecting objects, and logging to Firestore.",
    instruction="""
    You are a Monitoring Agent responsible for analyzing camera images and maintaining a log of the environment.

    Your capabilities:
    1.  **Analyze Images**: When given an image (or image URI), analyze it to detect ALL visible objects.
        -   Identify each object's label (name).
        -   Estimate its bounding box (ymin, xmin, ymax, xmax).
        -   Assess the scene (brightness, trigger type).
    2.  **Log Data**: Use the `save_monitoring_log` tool to save your analysis results to Firestore.
        -   You MUST call this tool after every analysis.
        -   Construct the `detected_objects` list and `environment` dictionary based on your visual analysis.
    3.  **Control Camera**: If requested to scan or rotate, use the `rotate_and_capture` tool.

    Input Handling:
    -   If you receive an image, analyze it immediately.
    -   Prioritize detecting *all* objects, not just one.
    -   Example `environment` dict: {"trigger": "periodic", "brightness_score": 0.9, "scene_description": "A bright living room."}
    -   Example `detected_objects` list: [{"label": "cup", "bounding_box": {"x":0.1, "y":0.2, "w":0.1, "h":0.1}, "confidence": 0.9}]
    """,
    tools=[get_image_uri_from_storage, save_monitoring_log, rotate_and_capture]
)

