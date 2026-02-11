from typing import Dict, Any, List
import json
from google.adk.agents import Agent
from app.coco_agent.prompts.loader import load_prompt
from app.coco_agent.tools.storage_tools import get_image_uri_from_storage
from app.coco_agent.tools.firestore_tools import save_monitoring_log
from app.services.monitoring_service import get_monitoring_service
from google.genai import types


def suspend_monitoring(reason: str = "explorer_request", duration: int = 300) -> str:
    """
    監視ループを一時停止します。Explorer Agent がカメラを操作する前に呼び出してください。

    Args:
        reason: 一時停止の理由（例: "explorer_request", "user_request"）
        duration: 一時停止の最大期間（秒）。この期間が過ぎると自動的に再開されます。

    Returns:
        一時停止の結果メッセージ。
    """
    service = get_monitoring_service()
    result = service.suspend(reason=reason, duration=duration)
    return json.dumps(result, ensure_ascii=False)


def resume_monitoring() -> str:
    """
    一時停止中の監視ループを再開します。Explorer Agent の操作が完了した後に呼び出してください。

    Returns:
        再開の結果メッセージ。
    """
    service = get_monitoring_service()
    result = service.resume()
    return json.dumps(result, ensure_ascii=False)


def get_monitoring_status() -> str:
    """
    現在の監視ステータスを取得します（一時停止中か、誰が停止したか等）。

    Returns:
        監視ステータスの JSON 文字列。
    """
    service = get_monitoring_service()
    result = service.get_status()
    return json.dumps(result, ensure_ascii=False)


monitor_agent = Agent(
    name="monitor_agent",
    model="gemini-2.5-flash",
    description="固定画角のカメラ画像を継続的に分析し、物体検出結果をFirestoreにログする監視Agent。suspend/resumeによる排他制御をサポート。",
    instruction=load_prompt("monitor"),
    tools=[
        get_image_uri_from_storage,
        save_monitoring_log,
        suspend_monitoring,
        resume_monitoring,
        get_monitoring_status,
    ],
)
