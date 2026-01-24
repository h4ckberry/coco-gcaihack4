import os
import vertexai
from vertexai.preview import reasoning_engines
from langchain_google_vertexai import HarmBlockThreshold, HarmCategory

# ==============================================================================
# 1. Configuration & Setup
# ==============================================================================
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "fresh-producer-mmnnp")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

print(f"Initializing Vertex AI (ADK) with Project: {PROJECT_ID}, Location: {LOCATION}")
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Warning: Failed to initialize Vertex AI. Error: {e}")

# ==============================================================================
# 2. Define Tools (Sub-Agents)
# ==============================================================================

def call_context_historian(query: str) -> str:
    """
    Queries the Context Historian agent to search past observations in Firestore.
    Use this to find out where objects were seen in the past.
    """
    print(f"\n[Tool] Context Historian invoked with query: '{query}'")
    # In a real app, this would query Firestore
    return f"Context Historian found: 'The keys were last seen on the kitchen table at 10:00 AM today.'"

def call_realtime_observer(target_object: str) -> str:
    """
    Delegates to the Realtime Observer agent to analyze the current camera feed.
    Use this to check if an object is currently visible.
    """
    print(f"\n[Tool] Realtime Observer invoked for target: '{target_object}'")
    # In a real app, this would analyze the live image
    return f"Realtime Observer reports: 'I am looking at the kitchen table now, but I do NOT see the {target_object}.'"

def call_causal_detective(context_info: str) -> str:
    """
    Delegates to the Causal Detective agent to reason about a situation.
    Use this when you need to deduce why something happened or where it might be.
    """
    print(f"\n[Tool] Causal Detective invoked with context: '{context_info}'")
    return "Causal Detective hypothesis: 'Maybe the cat knocked them off.'"

def call_physical_explorer(action_instruction: str) -> str:
    """
    Delegates to the Physical Explorer agent to move the camera or robot.
    Use this to change the viewpoint if the object is not visible.
    """
    print(f"\n[Tool] Physical Explorer invoked with instruction: '{action_instruction}'")
    return f"Physical Explorer status: 'Executed {action_instruction}.'"

# ==============================================================================
# 3. Define the Orchestrator Agent using Reasoning Engine (ADK)
# ==============================================================================
# The LangchainAgent class from reasoning_engines is the key ADK component.
# It wraps a Gemini model and manages the tool calling loop automatically.

# Define the safety settings
safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

# Create the agent
agent = reasoning_engines.LangchainAgent(
    model="gemini-1.5-pro-001",  # Use Pro for Orchestrator
    tools=[
        call_context_historian,
        call_realtime_observer,
        call_causal_detective,
        call_physical_explorer
    ],
    model_kwargs={
        "temperature": 0.0,
        "safety_settings": safety_settings,
    },
    system_instruction="""
    You are the Orchestrator Agent for the Janus / Contextual Finder system.
    Your goal is to help the user find objects or understand the environment.
    
    You have access to a team of specialized agents (tools):
    - Context Historian: Knows about past locations.
    - Realtime Observer: Sees what is currently visible.
    - Causal Detective: Reasons about why things are missing.
    - Physical Explorer: Can move the camera.
    
    Plan a strategy, call the appropriate tools in a logical order, and provide a final answer to the user.
    Example strategy: Check current view -> Check history -> Deduce -> Explore.
    """
)

# ==============================================================================
# 4. Main Execution
# ==============================================================================
if __name__ == "__main__":
    print("\n>>> TEST CASE: Where are my keys?")
    
    try:
        # The query method handles the agent loop (Thought -> Action -> Observation -> Final Answer)
        response = agent.query(input="Where are my keys?")
        print(f"\nFinal Response:\n{response['output']}")
    except Exception as e:
        print(f"Error executing agent: {e}")