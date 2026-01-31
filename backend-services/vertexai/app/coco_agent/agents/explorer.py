from google.adk.agents.llm_agent import Agent

# Explorer Agent
# Responsible for searching information (Placeholders for now).

explorer_agent = Agent(
    name="explorer_agent",
    model="gemini-2.5-flash",
    description="Agent for searching information.",
    instruction="You are an Explorer Agent. You help users find information."
)
