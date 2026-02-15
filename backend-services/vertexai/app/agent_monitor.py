import logging
logging.getLogger("google.adk").setLevel(logging.INFO)
import os
import sys
import json
from typing import Any

# =================================================================
# 1. Path Configuration (Required for direct execution)
# =================================================================
if __name__ == "__main__" and "app" not in sys.modules:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

# =================================================================
# 2. Third-party & Environment Initialization
# =================================================================
import vertexai
from dotenv import load_dotenv

# Load environment variables immediately
load_dotenv()

# If API key is present and we haven't explicitly chosen a backend, default to AI Studio for local dev
if os.environ.get("GOOGLE_API_KEY") and "GOOGLE_GENAI_USE_VERTEXAI" not in os.environ:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

# Explicitly initialize vertexai before other components use it
try:
    vertexai.init(
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION")
    )
except Exception as e:
    logging.getLogger(__name__).warning(f"Vertex AI initialization skipped or failed: {e}")

from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.cloud import logging as google_cloud_logging
from vertexai.agent_engines.templates.adk import AdkApp
from google.adk.apps import App

# =================================================================
# 3. Local Application Imports
# =================================================================
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback
from app.app_utils.logging_config import configure_logging
from app.coco_agent.agents.monitor import monitor_agent
from app.services.monitoring_service import get_monitoring_service

# =================================================================
# 4. Global State & App Wrapper Definitions
# =================================================================
gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

logger = logging.getLogger(__name__)


class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Initialize the agent engine app with logging and telemetry."""
        vertexai.init()
        # setup_telemetry() # Disabling telemetry to prevent SSLEOFError in Cloud Run
        super().set_up()
        configure_logging()
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location


    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

# app/agent_monitor.py の修正版

    async def chat(self, session_id: str, user_input: str, user_id: str = "default-user") -> dict[str, Any]:
        """Chats with the agent.
        
        注意: セッション永続化の問題を回避するため、
        Runnerのセッション管理を使わず、毎回新規セッションを作成します。
        """
        logger.info(f"DEBUG: chat called with session_id={session_id}, user_input={user_input}, user_id={user_id}")

        if not user_input:
            return {"error": "user_input is required"}

        from google.adk.runners import InMemoryRunner
        from google.genai import types

        # InMemoryRunnerを使用（Vertex AIセッションサービスの問題を回避）
        runner = InMemoryRunner(
            app=monitor_app
        )

        # 新しいセッションを作成
        try:
            # session_idを識別子として使いながら、実際は毎回新規作成
            import uuid
            temp_session_id = f"session-{uuid.uuid4().hex[:8]}"
            
            session = await runner.session_service.create_session(
                app_name="monitor_agent",
                user_id=user_id,
                session_id=temp_session_id
            )
            
            actual_session_id = session.id
            logger.info(f"Created temporary session: {actual_session_id}")
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}", exc_info=True)
            return {"error": f"Session creation failed: {str(e)}"}

        full_text = ""
        try:
            # Runnerを実行
            async for event in runner.run_async(
                user_id=user_id,
                session_id=actual_session_id,
                new_message=types.Content(parts=[types.Part(text=user_input)])
            ):
                if hasattr(event, "content") and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            full_text += part.text
                            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            return {"error": f"Agent execution failed: {str(e)}"}
        
        if not full_text:
            return {"output": "Agent completed task without text output."}

        return {"output": full_text}


    async def create_user_session(self, user_id: str = "default-user") -> dict[str, Any]:
        """Creates a new session ID for the user.
        
        Returns a simple UUID that can be used with the chat method.
        The actual Vertex AI session will be created/managed by the Runner.
        """
        import uuid
        
        logger.info(f"DEBUG: create_user_session called with user_id={user_id}")
        
        # シンプルなUUIDを生成
        # Runnerが実際のVertex AIセッションを管理するため、
        # ここでは識別子を生成するだけで良い
        session_id = uuid.uuid4().hex[:16]
        
        logger.info(f"Generated session_id: {session_id}")
        return {"session_id": session_id}

    # ... (existing register_operations) ...

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent."""
        operations = super().register_operations()
        # Ensure our sync methods are correctly exposed
        operations[""] = operations.get("", []) + ["register_feedback", "chat", "create_user_session"]
        return operations

# Global App Wrappers
monitor_app = App(root_agent=monitor_agent, name="monitor_agent")

try:
    agent_engine = AgentEngineApp(
        app=monitor_app,
        artifact_service_builder=lambda: GcsArtifactService(bucket_name=logs_bucket_name)
        if logs_bucket_name
        else InMemoryArtifactService(),
    )
except Exception as e:
    logging.getLogger(__name__).warning(f"Agent Engine App initialization skipped or failed: {e}")
    agent_engine = None


# =================================================================
# 5. A2A / REST API Server Mode
# =================================================================
def create_a2a_app():
    """Monitor Agent を A2A + REST API 対応の Starlette アプリとして返す。

    A2A エンドポイント: / (A2A protocol - 画像分析等)
    REST エンドポイント:
        POST /api/suspend  - 監視の一時停止
        POST /api/resume   - 監視の再開
        GET  /api/status   - 監視ステータス確認

    起動:
        MONITOR_A2A_MODE=1 uvicorn app.agent_monitor:a2a_starlette_app --host 0.0.0.0 --port 8001
    """
    try:
        from google.adk.a2a.utils.agent_to_a2a import to_a2a
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        host = os.environ.get("MONITOR_A2A_HOST", "0.0.0.0")
        port = int(os.environ.get("MONITOR_A2A_PORT", "8001"))
        protocol = os.environ.get("MONITOR_A2A_PROTOCOL", "http")

        starlette_app = to_a2a(
            monitor_agent,
            host=host,
            port=port,
            protocol=protocol,
        )

        # --- REST API エンドポイントを追加 ---
        service = get_monitoring_service()

        async def api_suspend(request: Request) -> JSONResponse:
            """POST /api/suspend - 監視を一時停止"""
            try:
                body = await request.json()
            except Exception:
                body = {}
            reason = body.get("reason", "explorer_request")
            duration = body.get("duration", 300)
            result = service.suspend(reason=reason, duration=duration)
            return JSONResponse(result)

        async def api_resume(request: Request) -> JSONResponse:
            """POST /api/resume - 監視を再開"""
            result = service.resume()
            return JSONResponse(result)

        async def api_status(request: Request) -> JSONResponse:
            """GET /api/status - 監視ステータス取得"""
            result = service.get_status()
            return JSONResponse(result)

        # Starlette アプリにルートを追加
        starlette_app.routes.extend([
            Route("/api/suspend", api_suspend, methods=["POST"]),
            Route("/api/resume", api_resume, methods=["POST"]),
            Route("/api/status", api_status, methods=["GET"]),
        ])

        # 【追加】起動時に監視ループを開始する
        @starlette_app.on_event("startup")
        async def startup_event():
            logger.info("Starting Monitoring Loop via A2A App Startup...")
            # 非同期タスクとして監視サービスを開始
            import asyncio
            asyncio.create_task(service.start())

        # 【追加】終了時に停止する
        @starlette_app.on_event("shutdown")
        async def shutdown_event():
            logger.info("Stopping Monitoring Loop...")
            await service.stop()

        logging.getLogger(__name__).info(
            f"A2A + REST app created for Monitor Agent at {protocol}://{host}:{port}"
        )
        return starlette_app
    except ImportError as e:
        logging.getLogger(__name__).error(
            f"Failed to create A2A app: {e}. Install 'a2a-sdk' package."
        )
        return None

# A2A モードが有効な場合、Starlette アプリを module レベルで公開
a2a_starlette_app = None
if os.environ.get("MONITOR_A2A_MODE", "0") == "1":
    a2a_starlette_app = create_a2a_app()

# =================================================================
# 6. Entry Point (Local Execution)
# =================================================================
if __name__ == "__main__":
    import asyncio
    
    # A2A モードでの起動
    if os.environ.get("MONITOR_A2A_MODE", "0") == "1" or "--a2a" in sys.argv:
        import uvicorn
        setup_telemetry()
        host = os.environ.get("MONITOR_A2A_HOST", "0.0.0.0")
        port = int(os.environ.get("MONITOR_A2A_PORT", "8001"))
        print(f"[START] Starting Monitor Agent as A2A server on {host}:{port}...")

        app = create_a2a_app()
        if app:
            uvicorn.run(app, host=host, port=port)
        else:
            print("[ERROR] Failed to create A2A app. Check dependencies.")
            sys.exit(1)
            
    # ローカル対話モードでの起動
    else:
        from google.adk.runners import InMemoryRunner
        from google.genai import types

        async def main():
            setup_telemetry()
            print("[START] Starting Monitor Agent locally...")
            print("Type 'exit' or 'quit' to stop.")

            local_app = App(
                name="monitor_agent",
                root_agent=monitor_agent
            )

            runner = InMemoryRunner(
                app=local_app
            )

            # create_session is async, so we must await it
            session = await runner.session_service.create_session(
                session_id="local-debug-session",
                user_id="local-user",
                app_name="monitor_agent"
            )
            session_id = session.id
            user_id = session.user_id
            
            # Start Monitoring Loop Service
            monitoring_service = get_monitoring_service()
            await monitoring_service.start()
            print("[OK] Monitoring Service started.")

            print(f"[OK] Session created: {session_id}")

            while True:
                try:
                    # input() is blocking but acceptable for local debug script
                    # ideally use asyncio.to_thread for input to not block the loop
                    user_input = await asyncio.to_thread(input, "User: ")
                    
                    if user_input.lower() in ["exit", "quit"]:
                        break

                    print("Agent: ", end="", flush=True)
                    # InMemoryRunner.run is synchronous generator based on inspection
                    # but we are in async main, let's see. 
                    # If runner.run blocks, it blocks the monitoring loop.
                    # Use to_thread if run is purely sync blocking.
                    # ADK runner.run is sync generator.
                    
                    # To keep monitoring loop alive during agent processing, we should ideally run agent in thread.
                    # However, for simple input/output loop, standard ADK pattern:
                    
                    def run_turn(u_in):
                        # Clean surrogates to avoid pydantic serialization errors on some environments
                        u_in = u_in.encode('utf-8', 'ignore').decode('utf-8')
                        for event in runner.run(
                            user_id=user_id,
                            session_id=session_id,
                            new_message=types.Content(parts=[types.Part(text=u_in)])
                        ):
                           if hasattr(event, "content") and event.content and event.content.parts:
                                for part in event.content.parts:
                                     if part.text:
                                         print(part.text, end="", flush=True)
                        print()

                    await asyncio.to_thread(run_turn, user_input)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"\n[ERROR] Error: {e}")
            
            await monitoring_service.stop()

        asyncio.run(main())


