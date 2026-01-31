import logging
import os
from typing import Any

import vertexai
from dotenv import load_dotenv
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.cloud import logging as google_cloud_logging
from vertexai.agent_engines.templates.adk import AdkApp

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback
from app.coco_agent.agents.orchestrator import orchestrator_agent

# Load environment variables from .env file at runtime
load_dotenv()


class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Initialize the agent engine app with logging and telemetry."""
        vertexai.init()
        setup_telemetry()
        super().set_up()
        logging.basicConfig(level=logging.INFO)
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

# Wrap Orchestrator Agent
agent_engine = AgentEngineApp(
    app=orchestrator_agent,
    artifact_service_builder=lambda: GcsArtifactService(bucket_name=logs_bucket_name)
    if logs_bucket_name
    else InMemoryArtifactService(),
)

if __name__ == "__main__":
    import asyncio
    from google.adk.runners import InMemoryRunner
    from google.adk.apps import App
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    async def main():
        setup_telemetry()
        print("🚀 Starting Orchestrator Agent locally...")
        print("Type 'exit' or 'quit' to stop.")

        # Local execution uses standard ADK App wrapper
        local_app = App(
            name="orchestrator_agent",
            root_agent=orchestrator_agent
        )

        runner = InMemoryRunner(
            app=local_app
        )

        # create_session is async, so we must await it
        session = await runner.session_service.create_session(
            session_id="local-debug-session",
            user_id="local-user",
            app_name="orchestrator_agent"
        )
        session_id = session.id
        user_id = session.user_id

        print(f"✅ Session created: {session_id}")

        while True:
            try:
                # input() is blocking but acceptable for local debug script
                user_input = input("User: ")
                if user_input.lower() in ["exit", "quit"]:
                    break

                print("Agent: ", end="", flush=True)
                # InMemoryRunner.run is synchronous generator based on inspection
                for event in runner.run(
                    user_id=user_id,
                    session_id=session_id,
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
