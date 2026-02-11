import os
import logging
from app.coco_settings import get_coco_settings


logger = logging.getLogger(__name__)


_storage_client = None

def get_storage_client():
    """
    Returns the Storage client, initializing it if necessary.
    """
    global _storage_client
    if _storage_client is None:
        try:
            from google.cloud import storage
            from google.oauth2 import service_account
            
            settings = get_coco_settings()
            project_id = settings.GCLOUD_PROJECT_ID or os.environ.get("GOOGLE_CLOUD_PROJECT")
            
            # Explicitly load credentials if env var is set
            # Explicitly load credentials if env var is set
            key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            
            if key_path:
                if os.path.exists(key_path):
                    try:
                        creds = service_account.Credentials.from_service_account_file(key_path)
                        _storage_client = storage.Client(credentials=creds, project=project_id)
                        logger.info(f"Storage client initialized with service account: {key_path}")
                    except Exception as e:
                        logger.warning(f"Failed to load service account: {e}. Falling back to default.")
                        _storage_client = storage.Client(project=project_id)
                else:
                    _storage_client = storage.Client(project=project_id)
            else:
                _storage_client = storage.Client(project=project_id)
                logger.info(f"Storage client initialized (default auth) for project: {project_id}")
        except Exception as e:
            # We don't log error here to avoid spamming if credentials are missing
            _storage_client = None
    return _storage_client

def get_image_uri_from_storage(image_id: str) -> str:
    """
    指定された画像ID(ファイル名)に対応するFirebase Storage (GCS) のURIの文字列を生成します。

    Args:
        image_id (str): 画像のファイル名。
                        例: "20260124_100000.jpg"

    Returns:
        str: Geminiが参照可能なURI。
             例: "gs://ai-coco.firebasestorage.app/20260124_100000.jpg"
    """
    # 関数内で設定を読み込む（Lazy Loading）
    settings = get_coco_settings()
    bucket_name = settings.FIREBASE_STORAGE_BUCKET

    # 万が一設定が読み込めない場合のフォールバック
    if not bucket_name:
        bucket_name = "ai-coco.firebasestorage.app"

    # 1. 余計な空白などを削除
    filename = image_id.strip()

    # 2. 拡張子がなければ補完
    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        filename += ".jpg"

    # 3. gs:// URI の生成
    gcs_uri = f"gs://{bucket_name}/{filename}"

    return gcs_uri

def get_latest_image_uri(bucket_name: str = None) -> str:
    """
    Retrieves the GS URI of the latest uploaded image in the bucket.
    """
    settings = get_coco_settings()
    target_bucket = bucket_name or settings.FIREBASE_STORAGE_BUCKET or "ai-coco.firebasestorage.app"
    
    storage_client = get_storage_client()
    if not storage_client:
        # If client initialization failed (likely credentials), return a dummy or empty
        # For local testing, we might want to return a placeholder.
        # But for now, returning empty to signal failure without the exception trace.
        return ""
    
    try:
        bucket = storage_client.bucket(target_bucket)
        
        # List all blobs and sort by creation time
        blobs = list(bucket.list_blobs(max_results=100)) # Limit to 100 for performance
        
        if not blobs:
            return ""

        # Filter for images
        image_blobs = [b for b in blobs if b.name.lower().endswith((".jpg", ".jpeg", ".png"))]
        
        if not image_blobs:
            return ""
            
        # Sort by updated/created time descending
        latest_blob = max(image_blobs, key=lambda x: x.updated or x.time_created)
        
        return f"gs://{target_bucket}/{latest_blob.name}"
        
    except Exception as e:
        logger.warning(f"Failed to fetch latest image from GCS: {e}")
        return ""
