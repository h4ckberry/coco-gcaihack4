
import logging
import datetime
from typing import Optional, Any, Dict
from app.coco_agent.tools.firestore_tools import get_db

logger = logging.getLogger(__name__)

async def update_agent_state(
    session_id: str,
    agent_name: str,
    head_state: str = "Idle",    # Idle, Listening, Thinking, Found, Error
    body_action: str = "Idle",   # Idle, Waving, Happy
    message: str = "",
    mode: str = "Default"        # Monitoring, Inference, Search, Default
):
    """
    Updates the agent state in Firestore for real-time frontend feedback.
    """
    if not session_id:
        return

    db = get_db()
    if db is None:
        logger.warning(f"[Mock] Updating Agent State: {agent_name} - {message}")
        return

    try:
        doc_ref = db.collection("sessions").document(session_id)

        # Prepare update data
        data = {
            "agentName": agent_name,
            "headState": head_state,
            "bodyAction": body_action,
            "message": message,
            "mode": mode,
            "updatedAt": datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000 # milliseconds
        }

        # Use update if document exists, set with merge otherwise (safer)
        # Note: In async context, we might want to run this in executor or await if async client used.
        # But standard google-cloud-firestore is synchronous.
        # If running in async loop, this might block slightly.
        # For hackathon, direct call is acceptable.
        doc_ref.set(data, merge=True)
        # logger.debug(f"Updated agent state for session {session_id}: {data}")

    except Exception as e:
        logger.error(f"Failed to update agent state: {e}")

# High-level helpers based on context
async def set_agent_thinking(session_id: str, agent_name: str, message: str = "Thinking..."):
    await update_agent_state(session_id, agent_name, head_state="Thinking", body_action="Idle", message=message, mode="Inference")

async def set_agent_searching(session_id: str, agent_name: str, message: str = "Searching..."):
    await update_agent_state(session_id, agent_name, head_state="Thinking", body_action="Idle", message=message, mode="Search")

async def set_agent_moving(session_id: str, agent_name: str, message: str = "Moving camera..."):
    await update_agent_state(session_id, agent_name, head_state="Idle", body_action="Idle", message=message, mode="Search")

async def set_agent_found(session_id: str, agent_name: str, message: str = "Found it!"):
    await update_agent_state(session_id, agent_name, head_state="Found", body_action="Happy", message=message, mode="Default")

async def set_agent_speaking(session_id: str, agent_name: str, message: str = "Speaking..."):
    await update_agent_state(session_id, agent_name, head_state="Found", body_action="Happy", message=message, mode="Default")
