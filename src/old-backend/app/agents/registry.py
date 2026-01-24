import os
import vertexai
from vertexai.preview import reasoning_engines
from langchain_google_vertexai import HarmBlockThreshold, HarmCategory
from app.tools import toolbox

# Initialize Vertex AI
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "fresh-producer-mmnnp")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

# We initialize Vertex AI at the module level or inside a setup function
# Ideally, this should be done once at application startup.
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Warning: Failed to initialize Vertex AI in registry.py: {e}")

def create_orchestrator_agent():
    """
    Creates and returns the Orchestrator Agent using Google Gen AI ADK (Reasoning Engine).
    """
    
    # Define safety settings
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    # Define the system instruction for the Orchestrator
    system_instruction = """
    You are the Orchestrator Agent for the Janus / Contextual Finder system.
    Your goal is to help the user find objects or understand the environment based on their requests.
    
    You have access to a set of tools (specialized functions):
    - `search_firestore`: Use this to find out where objects were seen in the past (Context Historian role).
    - `log_observation`: Use this to record new findings if explicitly asked or important.
    - `analyze_latest_image`: Use this to see what is currently in front of the camera (Realtime Observer role).
    - `rotate_camera_motor`: Use this to move the camera view if the object is not visible (Physical Explorer role).
    
    Your Logic Flow:
    1. Understand the user's intent (e.g., "Where are my keys?", "What is on the table?").
    2. Decide which tool to call. 
       - If looking for a lost item, checking history (`search_firestore`) is often a good start.
       - If asking about the current view, use `analyze_latest_image`.
       - If the object is not found in the current view or history, you might hypothesize or move the camera (`rotate_camera_motor`).
    3. You can call multiple tools in sequence if needed.
    4. Provide a final, helpful natural language response to the user.
    """

    # Create the agent
    # We pass the functions directly from toolbox. 
    # The Reasoning Engine will generate the tool definitions from the python function signatures and docstrings.
    agent = reasoning_engines.LangchainAgent(
        model="gemini-1.5-pro-001", # Orchestrator uses Pro for better reasoning
        tools=[
            toolbox.search_firestore,
            toolbox.log_observation,
            toolbox.analyze_latest_image,
            toolbox.rotate_camera_motor
        ],
        model_kwargs={
            "temperature": 0.0,
            "safety_settings": safety_settings,
        },
        system_instruction=system_instruction
    )
    
    return agent

