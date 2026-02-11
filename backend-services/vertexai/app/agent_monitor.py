import logging
import os
import json
from typing import Any

import vertexai
from dotenv import load_dotenv
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.cloud import logging as google_cloud_logging
from vertexai.agent_engines.templates.adk import AdkApp

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback
from app.app_utils.logging_config import configure_logging
from app.coco_agent.agents.monitor import monitor_agent
from app.services.monitoring_service import get_monitoring_service
from google.adk.apps import App

# Load environment variables from .env file at runtime
load_dotenv()


class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Initialize the agent engine app with logging and telemetry."""
        vertexai.init()
        setup_telemetry()
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

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent."""
        operations = super().register_operations()
        operations[""] = operations.get("", []) + ["register_feedback"]
        return operations


gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

# Wrap Monitor Agent
monitor_app = App(root_agent=monitor_agent, name="monitor_agent")

agent_engine = AgentEngineApp(
    app=monitor_app,
    artifact_service_builder=lambda: GcsArtifactService(bucket_name=logs_bucket_name)
    if logs_bucket_name
    else InMemoryArtifactService(),
)


# --- A2A サーバーモード ---
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


if __name__ == "__main__":
    import asyncio
    import sys

    if os.environ.get("MONITOR_A2A_MODE", "0") == "1" or "--a2a" in sys.argv:
        import uvicorn

        setup_telemetry()
        host = os.environ.get("MONITOR_A2A_HOST", "0.0.0.0")
        port = int(os.environ.get("MONITOR_A2A_PORT", "8001"))
        print(f"🚀 Starting Monitor Agent as A2A server on {host}:{port}...")

        app = create_a2a_app()
        if app:
            uvicorn.run(app, host=host, port=port)
        else:
            print("❌ Failed to create A2A app. Check dependencies.")
            sys.exit(1)
    else:
        from google.adk.runners import InMemoryRunner
        from google.genai import types

        async def main():
            setup_telemetry()
            print("🚀 Starting Monitor Agent locally...")
            print("Type 'exit' or 'quit' to stop.")

            local_app = App(name="monitor_agent", root_agent=monitor_agent)
            runner = InMemoryRunner(app=local_app)
            session = await runner.session_service.create_session(
                session_id="local-debug-session",
                user_id="local-user",
                app_name="monitor_agent"
            )

            print(f"✅ Session created: {session.id}")
            while True:
                try:
                    user_input = input("User: ")
                    if user_input.lower() in ["exit", "quit"]:
                        break
                    print("Agent: ", end="", flush=True)
                    async for event in runner.run_async(
                        user_id=session.user_id,
                        session_id=session.id,
                        new_message=types.Content(parts=[types.Part(text=user_input)])
                    ):
                        if hasattr(event, "content") and event.content and event.content.parts:
                            for part in event.content.parts:
                                if part.text:
                                    print(part.text, end="", flush=True)
                    print()
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")

        asyncio.run(main())
