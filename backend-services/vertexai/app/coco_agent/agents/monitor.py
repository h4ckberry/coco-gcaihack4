from google.adk.agents.llm_agent import Agent
from ..tools.storage_tools import get_image_uri_from_storage

# Monitor Agent
# Responsible for camera feeds and image retrieval.

monitor_agent = Agent(
    name="monitor_agent",
    model="gemini-2.5-flash",
    description="Agent for monitoring camera feeds and retrieving images.",
    instruction="You are a Monitoring Agent. You can access camera feeds and retrieve images from storage.",
    tools=[get_image_uri_from_storage]
)
