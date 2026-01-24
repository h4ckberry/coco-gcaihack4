import functions_framework
from google.cloud import storage
from PIL import Image
import io

# 【設定】保存先（リサイズ用）のバケット名
DEST_BUCKET_NAME = "ai-coco-resize"
RESIZE_TARGET = (640, 640)

storage_client = storage.Client()

@functions_framework.cloud_event
def resize_image(cloud_event):
    try:
        data = cloud_event.data
        source_bucket_name = data["bucket"]
        file_name = data["name"]
        
        print(f"Processing original: {file_name} from {source_bucket_name}")

        source_bucket = storage_client.bucket(source_bucket_name)
        source_blob = source_bucket.blob(file_name)

        # 1. 元画像をダウンロード
        image_bytes = source_blob.download_as_bytes()
        img = Image.open(io.BytesIO(image_bytes))

        # 2. リサイズ処理
        # (iPhoneの回転情報を考慮して修正するなら ImageOps.exif_transpose を使うとより丁寧ですが今回は省略)
        img_resized = img.resize(RESIZE_TARGET)
        
        # 3. 別のバケット(ai-coco-resize)に保存
        # ファイル名はそのまま使用して紐付けを維持
        dest_bucket = storage_client.bucket(DEST_BUCKET_NAME)
        new_blob = dest_bucket.blob(file_name)
        
        out_byte_arr = io.BytesIO()
        img_resized.save(out_byte_arr, format='JPEG')
        
        new_blob.upload_from_string(out_byte_arr.getvalue(), content_type='image/jpeg')
        
        print(f"Resized and saved to: gs://{DEST_BUCKET_NAME}/{file_name}")
        return "Done"
    except Exception as e:
        # エラーをログに出すが、システムには「正常終了」として報告する
        print(f"Error occurred: {e}")
        print("Stopping retry loop by returning success status.")
        return "Failed but stopped"
