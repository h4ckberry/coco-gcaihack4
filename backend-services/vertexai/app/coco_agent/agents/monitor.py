from typing import Dict, Any, List
import json
from google.adk.agents import Agent
from ..prompts.loader import load_prompt
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
    instruction=load_prompt("monitor"),
    tools=[get_image_uri_from_storage, save_monitoring_log, rotate_and_capture]
)

