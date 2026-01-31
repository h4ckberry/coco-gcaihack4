from google.adk.agents.llm_agent import Agent

# Placeholder for Orchestrator Agent
# This agent will act as the router for user queries.

orchestrator_agent = Agent(
    name="orchestrator",
    model="gemini-2.5-flash",
    description="Orchestrator Agent that routes queries to specialized sub-agents.",
    instruction=(
        "You are the Orchestrator Agent. Your goal is to route user queries to the appropriate sub-agent.\n"
        "Available Agents:\n"
        "- Monitor Agent: For camera feeds and real-time data.\n"
        "- Explorer Agent: For searching information.\n"
        "- Reasoner Agent: For complex logic and data analysis.\n"
        "If a query can be answered directly or is a greeting, you can respond directly."
    )
)
