import logging
import datetime
from typing import Dict, Any, List, Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)

# Initialize Firestore Client
# Assumes GOOGLE_APPLICATION_CREDENTIALS is set or running in GCP environment
try:
    db = firestore.Client()
except Exception as e:
    logger.warning(f"Firestore client initialization failed: {e}. Using mock DB.")
    db = None

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
    if db is None:
        logger.info("[Mock] Saving to Firestore: " + str(detected_objects))
        return "mock_doc_id"

    timestamp = datetime.datetime.now(datetime.timezone.utc)
    doc_id = f"log_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    
    data = {
        "doc_id": doc_id,
        "timestamp": timestamp.isoformat(),
        "image_storage_path": image_storage_path,
        "motor_angle": motor_angle,
        "scan_session_id": scan_session_id,
        "is_blind_spot": False, # Placeholder logic
        "environment": environment,
        "detected_objects": detected_objects
    }

    try:
        db.collection("monitoring_logs").document(doc_id).set(data)
        logger.info(f"Saved monitoring log: {doc_id}")
        return doc_id
    except Exception as e:
        logger.error(f"Failed to save to Firestore: {e}")
        return ""

def search_logs(query_label: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches monitoring logs for a specific object label.
    """
    if db is None:
        return []

    try:
        # Note: This requires a composite index or simple query. 
        # For simplicity, we might query recent logs and filter in memory if volume is low,
        # or use array-contains if we flatten the labels.
        # Here we'll fetch recent logs and filter for flexibility.
        docs = db.collection("monitoring_logs").order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).limit(20).stream()

        results = []
        for doc in docs:
            data = doc.to_dict()
            for obj in data.get("detected_objects", []):
                if query_label.lower() in obj.get("label", "").lower():
                    results.append(data)
                    if len(results) >= limit:
                        return results
        return results
    except Exception as e:
        logger.error(f"Failed to search logs: {e}")
        return []

def get_recent_context(limit: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieves the most recent monitoring logs to establish context.
    """
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
