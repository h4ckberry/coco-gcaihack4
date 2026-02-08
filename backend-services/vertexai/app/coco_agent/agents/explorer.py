from google.adk.agents.llm_agent import Agent
from app.coco_agent.prompts.loader import load_prompt
from app.coco_agent.tools.firestore_tools import search_logs
from app.app_utils.obniz import ObnizController

obniz = ObnizController()

def rotate_to_target(angle: int) -> str:
    """
    Rotates the camera to the specified angle to face the target.
    """
    obniz.rotate(angle)
    return f"Camera rotated to target angle: {angle}"

explorer_agent = Agent(
    name="explorer_agent",
    model="gemini-2.5-flash",
    description="Agent for physically searching for objects and controlling the camera.",
    instruction=load_prompt("explorer"),
    tools=[search_logs, rotate_to_target]
)
