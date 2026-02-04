from google.adk.apps import App
from .coco_agent.agents.orchestrator import orchestrator_agent
from .agent_orchestrator import AgentEngineApp

# Use the Orchestrator Agent as the root
root_agent = orchestrator_agent

# Use AgentEngineApp for production features (resumability, logging, etc.)
app = AgentEngineApp(root_agent=root_agent, name="coco_search_agent")
