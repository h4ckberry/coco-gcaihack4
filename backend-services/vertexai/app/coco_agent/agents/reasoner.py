from google.adk.agents.llm_agent import Agent
from ..prompts.loader import load_prompt
from ..tools.firestore_tools import search_logs, get_recent_context

reasoner_agent = Agent(
    name="reasoner_agent",
    model="gemini-2.5-flash", # Using Flash for speed, but Pro is better for reasoning if available
    description="Agent for complex reasoning about object locations based on history.",
    instruction=load_prompt("reasoner"),
    tools=[search_logs, get_recent_context]
)
