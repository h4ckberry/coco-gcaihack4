"""
Firestore にダミーの monitoring_log を投入するスクリプト。
Usage:
    uv run python scripts/insert_dummy_log.py
"""
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

from google.cloud import firestore

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", os.environ.get("PROJECT_ID", "ai-coco"))

db = firestore.Client(project=PROJECT_ID)

now = datetime.datetime.now(datetime.timezone.utc)
doc_id = f"log_{now.strftime('%Y%m%d_%H%M%S')}_dummy_remote"

data = {
    "doc_id": doc_id,
    "timestamp": now,
    "image_path": "gs://ai-coco.firebasestorage.app/dummy/latest.jpg",
    "search_labels": ["remote", "remote control"],  # ← search_logs("remote") でヒットする
    "motor_angle": -90,  # ← リモコンの位置
    "scan_session_id": "dummy_test",
    "is_blind_spot": False,
    "environment": {
        "brightness_score": 3,
        "scene_description": "A living room scene with a remote control on the side table.",
        "trigger": "manual_test",
    },
    "detected_objects": [
        {
            "box_2d": [0.3, 0.4, 0.5, 0.6],
            "label": "remote control",
            "confidence": 0.92,
        }
    ],
}

db.collection("monitoring_logs").document(doc_id).set(data)
print(f"✅ Inserted: {doc_id}")
print(f"   label: remote / remote control")
print(f"   motor_angle: -90")
