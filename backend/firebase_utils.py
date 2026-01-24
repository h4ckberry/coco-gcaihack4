import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import base64
import datetime

# Initialize Firebase App
cred_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.initialize_app(cred)
        print("[Firebase] Initialized successfully.")
    except ValueError:
        print("[Firebase] Already initialized.")
else:
    print("[Firebase] Warning: serviceAccountKey.json not found. Firebase features will be disabled.")

db = firestore.client() if os.path.exists(cred_path) else None

def save_monitoring_data(image_bytes: bytes, metadata: dict):
    """
    Saves monitoring data to Firestore.
    - metadata: dict containing 'label', 'box_2d', 'found', etc.
    - image_bytes: raw image data
    """
    if not db:
        print("[Firebase] Skipping save (DB not initialized).")
        return

    timestamp = datetime.datetime.now()
    
    # Prepare document data
    doc_data = {
        "timestamp": timestamp,
        "found": metadata.get("found", False),
        "label": metadata.get("label"),
        "box_2d": metadata.get("box_2d"),
        "message": metadata.get("message"),
        "search_query": metadata.get("search_query", "monitoring"), # Default to monitoring if no query
    }

    # Handle Image:
    # Ideally use Storage, but for now we'll use Base64 in Firestore (limited to 1MB total doc size)
    # We'll resize or compress if needed in a real app, but here we assume the frontend sends a reasonable size
    # or we just save it. To be safe, let's truncate if too huge or just save.
    # For a hackathon/prototype, Base64 is easiest setup.
    
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    doc_data["image_base64"] = image_b64

    try:
        # Add to 'monitoring_logs' collection
        db.collection("monitoring_logs").add(doc_data)
        print(f"[Firebase] Saved monitoring log at {timestamp}")
    except Exception as e:
        print(f"[Firebase] Error saving to Firestore: {e}")
