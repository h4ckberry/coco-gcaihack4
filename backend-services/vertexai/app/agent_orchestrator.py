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
from app.app_utils.logging_config import configure_logging
from app.coco_agent.agents.orchestrator import orchestrator_agent
from google.adk.apps import App

# Load environment variables from .env file at runtime
load_dotenv()

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Session ID for conversation context")
    user_input: str = Field(..., description="User's input text")


class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Initialize the agent engine app with logging and telemetry."""
        vertexai.init()
        setup_telemetry()
        super().set_up()
        configure_logging()
        logging_client = google_cloud_logging.Client()
        # Use standard logger for app compatibility, but keep cloud logger if needed for structured logs?
        # The crash was due to self.logger.info() call on cloud logger. 
        # We will separate them or just use standard logger.
        # Let's use standard logger as self.logger.
        self.logger = logging.getLogger(__name__)
        self.cloud_logger = logging_client.logger(__name__)
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        # Use cloud logger for structured logging if available, else standard
        if hasattr(self, "cloud_logger"):
             self.cloud_logger.log_struct(feedback_obj.model_dump(), severity="INFO")
        else:
             self.logger.info(f"Feedback: {feedback_obj.model_dump()}")

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent."""
        operations = super().register_operations()
        operations[""] = operations.get("", []) + ["register_feedback", "chat"]
        return operations

    async def chat(self, session_id: str, user_input: str, user_id: str = "default-user") -> dict[str, Any]:
        """Chats with the agent using platform session service.

        Args:
            session_id: The session ID.
            user_input: The user input.
            user_id: The user ID.
        """
        print(f"DEBUG: chat called with session_id={session_id}, user_input={user_input}, user_id={user_id}")

        if not session_id:
            return {"error": "session_id is required"}
        if not user_input:
            return {"error": "user_input is required"}

        from google.adk.runners import Runner
        from google.genai import types

        # Get the session service from the platform (VertexAiSessionService)
        session_service = self._tmpl_attrs.get("session_service")
        if not session_service:
            return {"error": "Session service not available"}

        # Get or verify the session exists
        try:
            session = await session_service.get_session(
                app_name="orchestrator_agent",
                user_id=user_id,
                session_id=session_id
            )
            if not session:
                return {"error": f"Session {session_id} not found"}
        except Exception as e:
            print(f"ERROR getting session: {e}")
            return {"error": f"Failed to get session: {str(e)}"}

        # Create a Runner with the platform's session service
        runner = Runner(
            app=orchestrator_app,
            session_service=session_service
        )

        response_text = []

        # Variables to track speech content
        speech_text_from_tool = None

        try:
            # Run the agent
            async for event in runner.run_async(
                session_id=session.id,
                user_id=session.user_id,
                new_message=types.Content(parts=[types.Part(text=user_input)])
            ):
                try:
                    # Log event type for debugging
                    self.logger.info(f"Runner Event Type: {type(event)}")
                except Exception as e:
                    self.logger.warning(f"Failed to log event: {e}")

                if hasattr(event, "content") and event.content:
                     # 1. Capture text parts for fallback
                    if event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                response_text.append(part.text)
                            
                            # 2. Capture generate_speech tool calls
                            if part.function_call and part.function_call.name == "generate_speech":
                                try:
                                    args = part.function_call.args
                                    # Args can be huge dict or struct, need to parse carefully if it's not already dict
                                    # In ADK, args is usually a dict-like object
                                    if "text" in args:
                                        speech_text_from_tool = args["text"]
                                        self.logger.info(f"Captured speech from tool: {speech_text_from_tool[:50]}...")
                                except Exception as e:
                                    self.logger.error(f"Failed to parse generate_speech args: {e}")

        except Exception as e:
            print(f"ERROR during agent run: {e}")
            return {"error": f"Agent execution failed: {str(e)}"}

        # Determine final audio content
        # Priority: 
        # 1. Text from `generate_speech` tool call (if present)
        # 2. Accumulated text response (fallback)
        
        final_text = "".join(response_text)
        text_to_speak = speech_text_from_tool if speech_text_from_tool else final_text
        audio_content = ""

        if text_to_speak:
            from app.app_utils.tts import synthesize_text_async
            try:
                # Use the selected text for speech, with a 60s timeout for Leda model
                audio_content = await synthesize_text_async(text_to_speak, timeout=60.0)
            except Exception as e:
                # This catch is for any non-timeout errors in the await itself
                self.logger.error(f"TTS synthesis failed (critical): {e}")

        return {"output": final_text, "audio_content": audio_content}





gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

# Wrap Orchestrator Agent
# Platform provides session management via VertexAiSessionService automatically
orchestrator_app = App(
    root_agent=orchestrator_agent,
    name="orchestrator_agent"
)

agent_engine = AgentEngineApp(
    app=orchestrator_app,
    artifact_service_builder=lambda: GcsArtifactService(bucket_name=logs_bucket_name)
    if logs_bucket_name
    else InMemoryArtifactService(),
)

if __name__ == "__main__":
    import asyncio
    from google.adk.runners import InMemoryRunner
    from google.adk.apps import App
    from google.genai import types

    async def main():
        setup_telemetry()
        print("🚀 Starting Orchestrator Agent locally (DEBUG MODE)...")
        print("Type 'exit' or 'quit' to stop.\n")

        local_app = App(
            name="orchestrator_agent",
            root_agent=orchestrator_agent
        )

        runner = InMemoryRunner(
            app=local_app
        )

        session = await runner.session_service.create_session(
            session_id="local-debug-session",
            user_id="local-user",
            app_name="orchestrator_agent"
        )
        session_id = session.id
        user_id = session.user_id

        print(f"✅ Session created: {session_id}\n")

        while True:
            try:
                user_input = input("\n👤 User: ")
                if user_input.lower() in ["exit", "quit"]:
                    break

                print("\n--- イベントログ開始 ---")
                event_count = 0
                final_text_parts = []

                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=types.Content(parts=[types.Part(text=user_input)])
                ):
                    event_count += 1
                    author = getattr(event, "author", "?")
                    actions = getattr(event, "actions", None)

                    # イベント概要
                    print(f"\n📦 Event #{event_count} | author={author}")

                    # Actions (transfer_to_agent, function_call 等)
                    if actions:
                        if hasattr(actions, "transfer_to_agent") and actions.transfer_to_agent:
                            print(f"   🔀 transfer_to_agent → {actions.transfer_to_agent}")
                        if hasattr(actions, "escalate") and actions.escalate:
                            print(f"   ⬆️  escalate = {actions.escalate}")

                    # Content (テキスト, function_call, function_response)
                    if hasattr(event, "content") and event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                preview = part.text[:120].replace("\n", "\\n")
                                print(f"   💬 text: {preview}")
                                final_text_parts.append(part.text)
                            if hasattr(part, "function_call") and part.function_call:
                                fc = part.function_call
                                print(f"   🔧 function_call: {fc.name}({fc.args})")
                            if hasattr(part, "function_response") and part.function_response:
                                fr = part.function_response
                                resp_preview = str(fr.response)[:120]
                                print(f"   📋 function_response: {fr.name} → {resp_preview}")

                print(f"\n--- イベントログ終了 (計 {event_count} イベント) ---")
                print(f"\n🤖 最終応答: {''.join(final_text_parts) if final_text_parts else '(テキスト応答なし)'}")

            except KeyboardInterrupt:
                break
            except Exception as e:
                import traceback
                print(f"\n❌ Error: {e}")
                traceback.print_exc()

    asyncio.run(main())
