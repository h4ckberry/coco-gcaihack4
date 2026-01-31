from google.adk.agents.llm_agent import Agent

# Reasoner Agent
# Responsible for complex reasoning.

reasoner_agent = Agent(
    name="reasoner_agent",
    model="gemini-2.5-flash",
    description="Agent for complex reasoning and analysis.",
    instruction="You are a Reasoner Agent. You analyze data and provide deep insights."
)
