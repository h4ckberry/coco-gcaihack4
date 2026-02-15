import logging
import datetime
import os
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from google.adk.tools import ToolContext
from app.coco_settings import get_coco_settings

logger = logging.getLogger(__name__)

_db = None

def get_db():
    """
    Returns the Firestore client, initializing it if necessary.
    """
    global _db
    if _db is None:
        try:
            # We explicitly allow setting project ID from setting if env is missing
            settings = get_coco_settings()
            project_id = settings.GCLOUD_PROJECT_ID or os.environ.get("GOOGLE_CLOUD_PROJECT")

            _db = firestore.Client(project=project_id)
            logger.info(f"Firestore client initialized for project: {project_id}")
        except Exception as e:
            logger.warning(f"Firestore client initialization failed: {e}. Using mock DB.")
            _db = None
    return _db


def save_monitoring_log(
    image_storage_path: str,
    detected_objects: List[Dict[str, Any]],
    environment: Dict[str, Any],
    motor_angle: int = 0,
    scan_session_id: Optional[str] = None
) -> str:
    """
    Saves monitoring data to Firestore 'monitoring_logs' collection.
    """
    db = get_db()
    if db is None:
        logger.info("[Mock] Saving to Firestore: " + str(detected_objects))
        return "mock_doc_id"

    # Generate timestamp and doc_id
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now

    # Generate clean ID using timestamp and session/suffix
    doc_id = f"log_{now.strftime('%Y%m%d_%H%M%S')}_{scan_session_id or 'manual'}"

    # Generate search_labels for efficient querying
    # Ensure we handle detected_objects which might have 'label' or 'name'
    search_labels = []
    for obj in detected_objects:
        label = obj.get("label") or obj.get("name")
        if label:
            search_labels.append(label.lower())

    data = {
        "doc_id": doc_id,
        "timestamp": timestamp, # Firestore handles datetime objects directly
        "image_path": image_storage_path, # Renamed from image_storage_path as per design
        "search_labels": search_labels, # Added for array-contains queries

        "motor_angle": motor_angle,
        "scan_session_id": scan_session_id or "manual_scan",
        "is_blind_spot": False, # Placeholder logic

        "environment": environment, # Expected to contain brightness_score, scene_description, etc.
        "detected_objects": detected_objects # Keep detailed objects with confidence
    }

    try:
        db.collection("monitoring_logs").document(doc_id).set(data)
        logger.info(f"Saved monitoring log: {doc_id}")
        return doc_id
    except Exception as e:
        logger.error(f"Failed to save to Firestore: {e}")
        return ""

from google.adk.tools import ToolContext
from app.services.state_service import set_agent_searching, set_agent_thinking

async def search_logs(query_label: str, limit: int = 5, tool_context: ToolContext = None) -> List[Dict[str, Any]]:
    """
    Searches monitoring logs for a specific object label.
    """
    session_id = tool_context.session.id if tool_context and tool_context.session else "default"
    await set_agent_searching(session_id, "explorer_agent", f"Searching logs for '{query_label}'...")

    db = get_db()

    if db is None:
        logger.info(f"[Mock] Searching logs for: {query_label}")
        return []

    try:
        # Use array-contains query on search_labels
        # Note: We removed .order_by("timestamp") to avoid requiring a specific composite index.
        # We will fetch slightly more docs and sort in memory.
        docs_stream = db.collection("monitoring_logs").where(
            filter=firestore.FieldFilter("search_labels", "array_contains", query_label.lower())
        ).limit(limit * 3).stream() # Fetch 3x limit to sorting space

        results = [doc.to_dict() for doc in docs_stream]
        
        # Client-side sort by timestamp descending
        # Ensure timestamp field exists and is comparable (handle None)
        results.sort(key=lambda x: x.get("timestamp", datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)), reverse=True)
        
        # Apply limit after sorting
        results = results[:limit]

        logger.info(f"Search found {len(results)} logs for '{query_label}'")
        return results
    except Exception as e:
        logger.error(f"Failed to search logs: {e}")
        return []

async def get_recent_context(limit: int = 3, tool_context: ToolContext = None) -> List[Dict[str, Any]]:
    """
    Retrieves the most recent monitoring logs to establish context.
    """
    session_id = tool_context.session.id if tool_context and tool_context.session else "default"
    await set_agent_thinking(session_id, "reasoner_agent", "Retrieving recent context...")

    db = get_db()
    if db is None:
        return []

    try:
        docs = db.collection("monitoring_logs").order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).limit(limit).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"Failed to get recent context: {e}")
        return []

