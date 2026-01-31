import os
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv

class Settings:
    def __init__(self):
        # 変数定義時にロードすることで、インポート時の副作用を防ぐ
        load_dotenv()

        # 必須項目（ない場合はNoneが入りますが、起動自体は阻止しません）
        self.GCLOUD_PROJECT_ID: Optional[str] = os.getenv("GCLOUD_PROJECT_ID")
        self.FIREBASE_STORAGE_BUCKET: Optional[str] = os.getenv("FIREBASE_STORAGE_BUCKET")

        # 任意項目（デフォルト値あり）
        self.GCLOUD_LOCATION: str = os.getenv("GCLOUD_LOCATION", "us-central1")
        self.DB_COLLECTION_NAME: str = os.getenv("DB_COLLECTION_NAME", "receipts")

# キャッシュ化は一旦外してシンプルにします（Pickleエラー回避のため）
# @lru_cache()
def get_settings():
    return Settings()
