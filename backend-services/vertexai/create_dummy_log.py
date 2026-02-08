import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime

# Initialize Firebase Admin
cred = credentials.Certificate('app/credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()
print(f"🔥 Connected to Firestore Project ID: {db.project}")

def create_dummy_log():
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    doc_id = f"log_{timestamp.strftime('%Y%m%d_%H%M%S')}_dummy"

    detected_objects = [
        {"label": "key", "confidence": 0.95, "box_2d": [0.4, 0.4, 0.5, 0.5]},
        {"label": "remote", "confidence": 0.90, "box_2d": [0.2, 0.2, 0.3, 0.3]},
        {"label": "lighter", "confidence": 0.85, "box_2d": [0.6, 0.6, 0.7, 0.7]}
    ]

    search_labels = [obj["label"] for obj in detected_objects]

    data = {
        "doc_id": doc_id,
        "timestamp": timestamp,
        "image_path": "gs://ai-coco.firebasestorage.app/dummy/latest.jpg",
        "search_labels": search_labels,
        "motor_angle": 90,  # Dummy angle for testing
        "scan_session_id": "dummy_scan",
        "is_blind_spot": False,
        "environment": {
            "trigger": "manual_test",
            "brightness_score": 1.0,
            "scene_description": "A test scene with a key, a remote, and a lighter."
        },
        "detected_objects": detected_objects
    }

    try:
        db.collection("monitoring_logs").document(doc_id).set(data)
        print(f"✅ Created dummy log: {doc_id}")
        print(f"   Labels: {search_labels}")
        print(f"   Angle: {data['motor_angle']}")
    except Exception as e:
        print(f"❌ Failed to create dummy log: {e}")

if __name__ == "__main__":
    create_dummy_log()
