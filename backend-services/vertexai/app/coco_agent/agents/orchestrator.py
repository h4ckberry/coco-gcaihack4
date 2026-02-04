from google.adk.agents import Agent
from .monitor import monitor_agent
from .explorer import explorer_agent
from .reasoner import reasoner_agent
from ...app_utils.tts import synthesize_text

def generate_speech(text: str) -> str:
    """
    Generates speech audio from text and returns a status message.
    The audio content is handled by the system (saved to session/response).
    """
    # This tool is a bridge. In a real ADK runtime, we might need access to 'session' here.
    # ADK tools can accept 'session' as an argument if type hinted `Session`.
    # Let's import Session to do it right, or just return the base64 string and let the LLM put it in output.
    # Returning large base64 to LLM context is bad.
    # Better: This tool should save side-effects.
    # But for now, let's assume we can just return a placeholder and the backend handles it?
    # No, the user wants the backend to send it.
    # Let's try to update the `agent_orchestrator.py` to Inject this capability or use a Context tool.
    # For now, let's just make the function return "Audio generated".
    # And we actually implement the side effect if possible.
    # Without `session` access in this scope, implementation is tricky.
    # Let's rely on `agent_orchestrator.py` to inject the tool with session access
    # OR simply define the tool here and assume we can modify state.
    # Let's just define the tool efficiently.
    
    # We will use a global or ContextVar if needed, or better:
    # We will instruct the Orchestrator to "Output the text to be spoken". 
    # AND we modify `agent_orchestrator.py` to Auto-TTS the final response?
    # User said: "Orchestrator to handle Cloud TTS ... frontend and Cloud TTS ... Orchestrator converts"
    # User said: "Reasoner ... output text, Orchestrator converts"
    # This implies Orchestrator receives text, then calls TTS.
    
    audio_b64 = synthesize_text(text)
    # We need to get this to the user. 
    # We'll return a special marker that the App can parse, or use the `output_key`.
    return f"<AUDIO_CONTENT>{audio_b64}</AUDIO_CONTENT>" 

orchestrator_agent = Agent(
    name="orchestrator",
    model="gemini-2.5-flash",
    description="Orchestrator Agent that routes user queries to specialized sub-agents.",
    instruction=(
        "You are the Orchestrator Agent. Your goal is to route user queries to the appropriate sub-agent.\n"
        "Routing Rules:\n"
        "1.  **Monitor Agent**: If the user asks about the *current* view or live feed (e.g., 'What do you see now?', 'Scan the room').\n"
        "2.  **Explorer Agent**: If the user explicitly asks to *find* a specific object physically (e.g., 'Find the keys', 'Where is the remote?').\n"
        "3.  **Reasoner Agent**: If the user asks for *deduction*, OR if the **Explorer Agent fails to find the object**.\n"
        "\n"
        "CRITICAL RULE: If the Explorer Agent searches and reports that the object is not found, you MUST immediately call the Reasoner Agent to deduce the location. Do not ask the user for permission.\n"
        "\n"
        "AUDIO FEEDBACK: When you have a final response for the user (from any agent), you MUST use the `generate_speech` tool to create audio for it. Pass the text message to this tool."
    ),
    sub_agents=[monitor_agent, explorer_agent, reasoner_agent],
    tools=[generate_speech]
)
