from google.adk.agents.llm_agent import Agent
from app.coco_agent.prompts.loader import load_prompt
from app.coco_agent.tools.firestore_tools import search_logs
from app.app_utils.obniz import ObnizController

obniz = ObnizController()

from google.adk.tools import ToolContext
from app.services.state_service import set_agent_moving

async def rotate_to_target(angle: int, tool_context: ToolContext = None) -> str:
    """
    Rotates the camera to the specified angle to face the target.
    Args:
        angle (int): The target angle in degrees.
        tool_context: ToolContext (Injected by ADK)
    """
    session_id = tool_context.session.id if tool_context and tool_context.session else "default"
    await set_agent_moving(session_id, "explorer_agent", f"Rotating camera to {angle}...")

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
    model="gemini-2.0-flash",
    description="Agent for physically searching for objects and controlling the camera.",
    instruction=load_prompt("explorer"),
    tools=[search_logs, rotate_to_target],
    output_key="explorer_result",
    disallow_transfer_to_peers=True,
)
