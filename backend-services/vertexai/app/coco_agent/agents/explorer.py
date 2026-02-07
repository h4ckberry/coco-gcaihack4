from google.adk.agents.llm_agent import Agent
from ..tools.firestore_tools import search_logs
from ...app_utils.obniz import ObnizController

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
    instruction="""
    You are an Explorer Agent. Your job is to find the physical location of objects requested by the user.

    Your capability:
    1.  **Search History**: Use `search_logs` to find where an object was previously seen.
    2.  **Move Camera**: If a location (angle) is found in the logs, use `rotate_to_target` to look at that spot.

    Process:
    -   When asked to find an object (e.g., "Where is the remote?"), search the logs first.
    -   If found, extract the `motor_angle` from the log and rotate the camera.
    -   Report your action (e.g., "I found a record of the remote at 45 degrees. Turning camera...").
    -   If not found, report that you cannot find it in the logs.
    """,
    tools=[search_logs, rotate_to_target]
)
