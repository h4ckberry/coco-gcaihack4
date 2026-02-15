# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
from typing import Any

import vertexai
from dotenv import load_dotenv
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.cloud import logging as google_cloud_logging
from vertexai.agent_engines.templates.adk import AdkApp

# from app.coco_agent.agents.orchestrator import orchestrator_agent
# from google.adk.apps import App
# orchestrator_app = App(root_agent=orchestrator_agent, name="orchestrator")
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

# Load environment variables from .env file at runtime
load_dotenv()

logger = logging.getLogger(__name__)


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

    def query(self, query: str, user_id: str = "default", session_id: str = "default") -> str:
        """Synchronous query method for sync callers."""
        from google.adk.runners import InMemoryRunner
        from google.genai import types
        
        # Use the imported app instance
        # Ensure orchestrator_app is available (it is defined at module level below)
        runner = InMemoryRunner(app=orchestrator_app)
        
        full_text = ""
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(parts=[types.Part(text=query)])
        ):
            try:
                # Log only event type and basic info to avoid clutter, or full event if debugging
                logger.info(f"Runner Event Type: {type(event)}")
                # logger.info(f"Runner Event Content: {event}") # Uncomment for full verbose logs
            except Exception as e:
                logger.warning(f"Failed to log event: {e}")

            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        full_text += part.text
        
        if not full_text.strip():
            logger.warning("Agent produced empty response text.")
            return "Agent completed task without text output (Check logs for tool execution)."
        
        return full_text

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent."""
        operations = super().register_operations()
        operations[""] = operations.get("", []) + ["register_feedback", "query"]
        return operations


gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

# Move imports here to avoid circular dependencies
from app.coco_agent.agents.orchestrator import orchestrator_agent
from google.adk.apps import App
orchestrator_app = App(root_agent=orchestrator_agent, name="orchestrator")

agent_engine = AgentEngineApp(
    app=orchestrator_app,
    artifact_service_builder=lambda: GcsArtifactService(bucket_name=logs_bucket_name)
    if logs_bucket_name
    else InMemoryArtifactService(),
)
