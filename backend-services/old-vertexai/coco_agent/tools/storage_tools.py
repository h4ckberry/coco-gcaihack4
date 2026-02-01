from ..settings import get_settings

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
    settings = get_settings()
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
