import os
import sys
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# デバッグ用: ログに読み込みを表示
print("DEBUG: Loading settings.py...", file=sys.stderr)

class CocoSettings(BaseSettings):
    # ▼▼▼ 今回の追加修正 ▼▼▼
    # Googleが勝手に渡してくる変数を「受け皿」として定義してエラーを防ぐ
    # これがあれば extra="ignore" が効かなくても確実に回避できます
    project_id: Optional[str] = None
    location_id: Optional[str] = None
    bucket_name: Optional[str] = None
    # ▲▲▲ 追加ここまで ▲▲▲

    # あなたのアプリで使う変数
    GCLOUD_PROJECT_ID: Optional[str] = None
    FIREBASE_STORAGE_BUCKET: Optional[str] = None

    # 任意項目（デフォルト値あり）
    GCLOUD_LOCATION: str = "us-central1"
    DB_COLLECTION_NAME: str = "receipts"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # 念のため残す
    )

    def __init__(self, **kwargs):
        load_dotenv()
        super().__init__(**kwargs)

# キャッシュ化は一旦外してシンプルにします
def get_coco_settings():
    return CocoSettings()