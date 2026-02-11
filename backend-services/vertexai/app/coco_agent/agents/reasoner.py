from google.adk.agents.llm_agent import Agent
from app.coco_agent.prompts.loader import load_prompt
from app.coco_agent.tools.firestore_tools import search_logs, get_recent_context

reasoner_agent = Agent(
    name="reasoner_agent",
    model="gemini-2.0-flash",
    description="Agent for complex reasoning about object locations based on history.",
    instruction=load_prompt("reasoner"),
    tools=[search_logs, get_recent_context],
    output_key="reasoner_result",
    disallow_transfer_to_peers=True,
)
