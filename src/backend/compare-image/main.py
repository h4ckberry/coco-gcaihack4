import functions_framework
from google.cloud import storage
from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity as ssim
import io
import requests
import google.auth.transport.requests
import google.oauth2.id_token

# ★★★ ステップ1で作ったCloud RunのURLをここに貼る ★★★
TARGET_RUN_URL = "https://simple-agent-xxxxx.us-west1.run.app"

SIMILARITY_THRESHOLD = 0.92
storage_client = storage.Client()

def trigger_cloud_run(file_name):
    print(f"Calling Cloud Run for {file_name}...")
    try:
        # 認証トークン作成
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, TARGET_RUN_URL)
        
        headers = {"Authorization": f"Bearer {id_token}"}
        payload = {"filename": file_name, "message": "Change detected!"}

        # POST送信 (timeout 5秒で十分)
        response = requests.post(TARGET_RUN_URL, json=payload, headers=headers, timeout=5)
        
        print(f"Cloud Run response status: {response.status_code}")
        return True
    except Exception as e:
        print(f"Failed to trigger Cloud Run: {e}")
        return False

@functions_framework.cloud_event
def compare_image(cloud_event):
    try:
        data = cloud_event.data
        bucket_name = data["bucket"]
        file_name = data["name"]
        
        # --- (ここから既存の画像比較ロジック) ---
        print(f"Start comparison for: {file_name}")
        bucket = storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs())
        image_blobs = [b for b in blobs if b.name.lower().endswith(('.jpg', '.jpeg', '.png'))]
        image_blobs.sort(key=lambda x: x.name, reverse=True)

        prev_blob = None
        for i, blob in enumerate(image_blobs):
            if blob.name == file_name:
                if i + 1 < len(image_blobs):
                    prev_blob = image_blobs[i+1]
                    break
        
        if prev_blob is None:
            print("Previous image not found. Skipped.")
            return "Skipped"

        blob_curr = bucket.blob(file_name)
        img_curr = Image.open(io.BytesIO(blob_curr.download_as_bytes())).convert('L')
        blob_prev = bucket.blob(prev_blob.name)
        img_prev = Image.open(io.BytesIO(blob_prev.download_as_bytes())).convert('L')

        img_curr_np = np.array(img_curr)
        img_prev_np = np.array(img_prev)

        if img_curr_np.shape != img_prev_np.shape:
            print("Dimension mismatch.")
            return "Error"

        score = ssim(img_prev_np, img_curr_np, data_range=255)
        print(f"--- SSIM Result: {score:.4f} ---")
        # --- (ここまで既存ロジック) ---

        # ★★★ 判定 & Cloud Run 起動 ★★★
        if score < SIMILARITY_THRESHOLD:
            print("【判定: 変化あり】Triggering Cloud Run...")
            trigger_cloud_run(file_name)  # <--- ここで起動！
        else:
            print("【判定: 変化なし】")

        return "Done"

    except Exception as e:
        print(f"[ERROR] {e}")
        return "Failed but stopped"
