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

from app.services.state_service import set_agent_speaking
from google.adk.tools import ToolContext

async def generate_speech(text: str, tool_context: ToolContext = None) -> str:
    """
    指定されたテキストを音声に変換します。最終回答をユーザに伝える際に使用してください。

    Args:
        text: 音声合成するテキスト
        tool_context: ToolContext (Injected by ADK)
    """
    session_id = tool_context.session.id if tool_context and tool_context.session else "default"
    await set_agent_speaking(session_id, "orchestrator", text)

    audio_b64 = synthesize_text(text)
    return f"<AUDIO_CONTENT>{audio_b64}</AUDIO_CONTENT>"


from google.adk.tools import ToolContext
from app.services.state_service import update_agent_state

# The original synchronous suspend_monitoring is replaced by the async version.
# The user provided a placeholder `pass` for the original, implying replacement.
async def suspend_monitoring_async(reason: str, duration: int = 300, tool_context: ToolContext = None) -> str:
    """
    Monitor Agent の自動監視ループを一時停止します。
    Explorer Agent にタスクを委譲する前に必ず呼び出してください。

    Args:
        reason: 一時停止の理由 (例: "explorer_request")
        duration: 停止する秒数 (デフォルト 300秒)
        tool_context: ToolContext (Injected by ADK)

    Returns:
        一時停止の結果メッセージ（JSON文字列）
    """
    session_id = tool_context.session.id if tool_context and tool_context.session else "default"

    # フロントエンドへの通知
    await update_agent_state(
        session_id=session_id,
        agent_name="orchestrator",
        head_state="Thinking",
        body_action="Idle",
        message=f"Suspending monitor for {reason}...",
        mode="Inference"
    )

    if MONITOR_AGENT_ENDPOINT:
        # A2A モード: Monitor の REST API を呼ぶ
        try:
            url = MONITOR_AGENT_ENDPOINT.rstrip("/") + "/api/suspend"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={"reason": reason, "duration": duration})
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


# The original synchronous resume_monitoring is replaced by the async version.
# The user provided a placeholder `pass` for the original, implying replacement.
async def resume_monitoring_async(tool_context: ToolContext = None) -> str:
    """
    一時停止中の監視を再開します。Explorer Agent の操作完了後に必ず呼び出してください。

    Args:
        tool_context: ToolContext (Injected by ADK)

    Returns:
        再開の結果メッセージ（JSON文字列）
    """
    session_id = tool_context.session.id if tool_context and tool_context.session else "default"

    # フロントエンドへの通知
    await update_agent_state(
        session_id=session_id,
        agent_name="orchestrator",
        head_state="Idle",
        body_action="Idle",
        message="Resuming monitoring...",
        mode="Monitoring"
    )

    if MONITOR_AGENT_ENDPOINT:
        # A2A モード
        try:
            url = MONITOR_AGENT_ENDPOINT.rstrip("/") + "/api/resume"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url)
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
        suspend_monitoring_async,
        resume_monitoring_async,
        get_calendar_events,
        create_calendar_event,
    ]
)
