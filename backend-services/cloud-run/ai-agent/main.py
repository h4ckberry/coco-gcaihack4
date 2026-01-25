import logging
import os
from io import BytesIO
from typing import Optional, Tuple

# Google Agent Developer Kit (ADK)
import google.adk as google_adk
import google.generativeai as genai
from dotenv import load_dotenv
from google.cloud import storage
from PIL import Image

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

# --- Configuration & Prompts (ADK Best Practice: Separate Config from Logic) ---

MODEL_NAME = "gemini-1.5-flash"

# Agent 1: Vision Specialist
VISION_INSTRUCTION = """You are a Vision Specialist.
Your job is to analyze images and provide detailed, objective descriptions of what you see.
Focus on objects, people, actions, and the environment."""

VISION_PROMPT = "Describe this scene in detail for the security log."

# Agent 2: Security Supervisor
SUPERVISOR_INSTRUCTION = """You are a Security Supervisor.
You receive field reports describing scenes.
Your task is to evaluate these reports for any security threats, safety hazards, or anomalies.
Output a status (SAFE/WARNING/DANGER) and a brief reasoning."""


class MultiAgentSystem:
    def __init__(self):
        self.bucket_name = os.getenv("BUCKET_NAME")
        self.api_key = os.getenv("GOOGLE_API_KEY")

        if not self.bucket_name:
            raise ValueError("BUCKET_NAME environment variable is not set")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")

        # Initialize Gemini API
        genai.configure(api_key=self.api_key)

        # --- Initialize Agents based on ADK Core Categories ---

        # 1. Specialist Agent: 画像解析の専門家
        # 役割: 画像を入力として受け取り、客観的な事実を詳細に描写する
        self.vision_config = google_adk.Agent(
            name="vision_specialist", model=MODEL_NAME
        )
        self.vision_specialist = genai.GenerativeModel(
            self.vision_config.model, system_instruction=VISION_INSTRUCTION
        )

        # 2. Orchestrator/Supervisor Agent: セキュリティ監督者
        # 役割: スペシャリストの報告を受けて、セキュリティリスクを判断する
        self.supervisor_config = google_adk.Agent(
            name="security_supervisor", model=MODEL_NAME
        )
        self.security_supervisor = genai.GenerativeModel(
            self.supervisor_config.model, system_instruction=SUPERVISOR_INSTRUCTION
        )

        # Initialize Google Cloud Storage Client
        self.storage_client = storage.Client()

    def get_latest_image(self) -> Optional[Tuple[Image.Image, str]]:
        """GCSバケットから最新の画像を取得する"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = list(bucket.list_blobs())

            # 画像ファイルのみをフィルタリング
            image_blobs = [
                b
                for b in blobs
                if b.name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".heic"))
            ]

            if not image_blobs:
                logger.warning(f"No images found in bucket {self.bucket_name}")
                return None

            # 更新日時でソートして最新を取得
            latest_blob = sorted(image_blobs, key=lambda x: x.updated, reverse=True)[0]
            logger.info(f"Latest image found: {latest_blob.name}")

            # データをメモリにダウンロードしてPIL Imageに変換
            image_data = latest_blob.download_as_bytes()
            image = Image.open(BytesIO(image_data))
            return image, latest_blob.name

        except Exception as e:
            logger.error(f"Error accessing Cloud Storage: {e}")
            raise

    def run(self):
        """エージェントの実行フロー"""
        logger.info("Starting Multi-Agent System...")
        result = self.get_latest_image()

        if result:
            image, filename = result
            logger.info(f"Processing image: {filename}")

            # --- Step 1: Vision Specialistによる解析 ---
            logger.info(">>> Vision Specialist is analyzing the scene...")
            # system_instruction is set in the model, so we just pass the prompt and image
            vision_response = self.vision_specialist.generate_content(
                [VISION_PROMPT, image]
            )
            scene_description = vision_response.text

            logger.info(f"\n--- [Vision Specialist Report] ---\n{scene_description}\n")

            # --- Step 2: Security Supervisorによる判断 ---
            logger.info(">>> Security Supervisor is evaluating the report...")
            supervisor_prompt = f"Review the following scene description and assess security status:\n\n{scene_description}"
            supervisor_response = self.security_supervisor.generate_content(
                supervisor_prompt
            )
            security_assessment = supervisor_response.text

            logger.info(
                f"\n--- [Security Supervisor Assessment] ---\n{security_assessment}\n"
            )
            logger.info("--------------------------------------")
        else:
            logger.info("No image to process.")


if __name__ == "__main__":
    system = MultiAgentSystem()
    system.run()
