from google.adk.agents.llm_agent import Agent
from app.coco_agent.prompts.loader import load_prompt
from app.coco_agent.tools.firestore_tools import search_logs
from app.app_utils.obniz import ObnizController

obniz = ObnizController()

def rotate_to_target(angle: int) -> str:
    """
    Rotates the camera to the specified angle to face the target.
    Args:
        angle (int): The target angle in degrees.
    """
    # Quantize to nearest 30 degrees as requested
    quantized_angle = round(angle / 30) * 30
    # Clamp to 0-180 range
    quantized_angle = max(0, min(180, quantized_angle))

    success = obniz.rotate(quantized_angle)
    if success:
        return f"Successfully rotated camera to target angle: {quantized_angle} (Input: {angle})"
    else:
        return f"Failed to rotate camera to angle: {quantized_angle}. Check connection or logs."

explorer_agent = Agent(
    name="explorer_agent",
    model="gemini-2.5-flash",
    description="Agent for physically searching for objects and controlling the camera.",
    instruction=load_prompt("explorer"),
    tools=[search_logs, rotate_to_target],
    output_key="explorer_result",
    disallow_transfer_to_peers=True,
)
