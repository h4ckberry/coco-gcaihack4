import functions_framework
from google.cloud import storage
from PIL import Image
import numpy as np
# from skimage.metrics import structural_similarity as ssim
import io
import requests
import google.auth.transport.requests
import google.oauth2.id_token
import os

TARGET_RUN_URL = os.environ.get("TARGET_RUN_URL")

# 閾値 (0.92あたりから調整)
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
    # ★★★ 【変更点】全体を try で囲み、エラー時にループしないようにする ★★★
    try:
        data = cloud_event.data
        bucket_name = data["bucket"] # 自動的に ai-coco-resize になります
        file_name = data["name"]

        print(f"Start comparison for: {file_name}")

        bucket = storage_client.bucket(bucket_name)

        # 1. バケット内の全ファイル一覧を取得
        # ai-coco-resize には縮小画像しかないので、prefixフィルタは不要
        blobs = list(bucket.list_blobs())
        
        # 画像のみ抽出し、ファイル名(日時)で新しい順にソート
        image_blobs = [b for b in blobs if b.name.lower().endswith(('.jpg', '.jpeg', '.png'))]
        image_blobs.sort(key=lambda x: x.name, reverse=True)

        # 2. 今回の画像の「1つ前」を探す
        prev_blob = None
        for i, blob in enumerate(image_blobs):
            if blob.name == file_name:
                if i + 1 < len(image_blobs):
                    prev_blob = image_blobs[i+1]
                    break
        
        if prev_blob is None:
            print("Previous image not found (First run?). Comparison skipped.")
            return "Skipped"

        print(f"Comparing Current: {file_name} vs Previous: {prev_blob.name}")

        # 3. 画像ダウンロード (サイズが小さいので高速)
        blob_curr = bucket.blob(file_name)
        # 画像データが壊れている場合などもここでキャッチされるようになります
        img_curr = Image.open(io.BytesIO(blob_curr.download_as_bytes())).convert('L') # 白黒化
        
        blob_prev = bucket.blob(prev_blob.name)
        img_prev = Image.open(io.BytesIO(blob_prev.download_as_bytes())).convert('L') # 白黒化

        # 4. SSIM比較
        img_curr_np = np.array(img_curr)
        img_prev_np = np.array(img_prev)

        # 画像サイズが一致しているか確認(念の為)
        if img_curr_np.shape != img_prev_np.shape:
            print("Image dimensions do not match. Skipping comparison.")
            return "Error"

        score = ssim(img_prev_np, img_curr_np, data_range=255)
        
        print(f"--- SSIM Result: {score:.4f} (Threshold: {SIMILARITY_THRESHOLD}) ---")

        # ★★★ 判定 & Cloud Run 起動 ★★★
        if score < SIMILARITY_THRESHOLD:
            print("【判定: 変化あり】Triggering Cloud Run...")
            trigger_cloud_run(file_name)  # <--- ここで起動！
        else:
            print("【判定: 変化なし】")

        return "Done"

    # ★★★ 【変更点】予期せぬエラーをキャッチして正常終了を偽装する ★★★
    except Exception as e:
        print(f"[ERROR] An exception occurred in compare_image: {e}")
        print("Stopping retry loop by returning success status.")
        # ここで値を返すとシステムは「処理完了」とみなし、再試行を行わない
        return "Failed but stopped"
