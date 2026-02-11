import os
import json
import logging

import httpx

from google.adk.agents import Agent
from app.coco_agent.prompts.loader import load_prompt
from .explorer import explorer_agent
from .reasoner import reasoner_agent
from app.app_utils.tts import synthesize_text
from app.coco_agent.tools.calendar_tools import get_calendar_events, create_calendar_event

logger = logging.getLogger(__name__)

# --- Monitor Agent の接続設定 ---
MONITOR_AGENT_ENDPOINT = os.environ.get("MONITOR_AGENT_ENDPOINT", "")

# A2A: Monitor Agent をリモートエージェントとして接続（画像分析用）
try:
    from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

    if MONITOR_AGENT_ENDPOINT:
        agent_card_url = MONITOR_AGENT_ENDPOINT.rstrip("/") + "/.well-known/agent.json"
        monitor_remote = RemoteA2aAgent(
            name="monitor_agent",
            description="リモートの監視Agent。固定画角カメラの画像分析とステータス確認専用。探索タスクは送らないこと。",
            agent_card=agent_card_url,
        )
        _use_a2a = True
    else:
        from .monitor import monitor_agent as monitor_remote
        _use_a2a = False
except ImportError:
    from .monitor import monitor_agent as monitor_remote
    _use_a2a = False

logger.info(f"Orchestrator: Monitor Agent mode = {'A2A Remote' if _use_a2a else 'Local Sub-Agent'}")


# --- Orchestrator のツール定義 ---

def generate_speech(text: str) -> str:
    """
    Generates speech audio from text and returns a status message.
    The audio content is handled by the system (saved to session/response).
    """
    audio_b64 = synthesize_text(text)
    return f"<AUDIO_CONTENT>{audio_b64}</AUDIO_CONTENT>"


def suspend_monitoring(reason: str = "explorer_request", duration: int = 300) -> str:
    """
    監視を一時停止します。Explorer Agent がカメラを操作する前に必ず呼び出してください。
    これにより、Monitor Agent の定期巡回が一時停止し、カメラの競合が防止されます。

    Args:
        reason: 一時停止の理由（例: "explorer_request"）
        duration: 一時停止の最大期間（秒）。この期間後に自動で再開されます。

    Returns:
        一時停止の結果メッセージ（JSON文字列）
    """
    if MONITOR_AGENT_ENDPOINT:
        # A2A モード: Monitor の REST API を呼ぶ
        try:
            url = MONITOR_AGENT_ENDPOINT.rstrip("/") + "/api/suspend"
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json={"reason": reason, "duration": duration})
                resp.raise_for_status()
                return json.dumps(resp.json(), ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to suspend monitoring via REST: {e}")
            return json.dumps({"status": "error", "message": f"監視の一時停止に失敗: {e}"}, ensure_ascii=False)
    else:
        # ローカルモード: 直接サービスを呼ぶ
        from app.services.monitoring_service import get_monitoring_service
        service = get_monitoring_service()
        result = service.suspend(reason=reason, duration=duration)
        return json.dumps(result, ensure_ascii=False)


def resume_monitoring() -> str:
    """
    一時停止中の監視を再開します。Explorer Agent の操作完了後に必ず呼び出してください。

    Returns:
        再開の結果メッセージ（JSON文字列）
    """
    if MONITOR_AGENT_ENDPOINT:
        # A2A モード: Monitor の REST API を呼ぶ
        try:
            url = MONITOR_AGENT_ENDPOINT.rstrip("/") + "/api/resume"
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url)
                resp.raise_for_status()
                return json.dumps(resp.json(), ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to resume monitoring via REST: {e}")
            return json.dumps({"status": "error", "message": f"監視の再開に失敗: {e}"}, ensure_ascii=False)
    else:
        from app.services.monitoring_service import get_monitoring_service
        service = get_monitoring_service()
        result = service.resume()
        return json.dumps(result, ensure_ascii=False)


# --- Orchestrator Agent 定義 ---
orchestrator_agent = Agent(
    name="orchestrator",
    model="gemini-2.0-flash",
    description="Orchestrator Agent that routes user queries to specialized sub-agents.",
    instruction=load_prompt("orchestrator"),
    sub_agents=[monitor_remote, explorer_agent, reasoner_agent],
    tools=[
        generate_speech,
        suspend_monitoring,
        resume_monitoring,
        get_calendar_events,
        create_calendar_event,
    ]
)
