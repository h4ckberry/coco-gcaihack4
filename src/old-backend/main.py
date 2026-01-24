import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.agents.registry import create_orchestrator_agent
from app.tools.tts import synthesize_speech

app = FastAPI(title="Janus Contextual Finder Backend")

# Initialize Orchestrator Agent (ADK)
# This creates the LangchainAgent backed by Vertex AI Reasoning Engine
try:
    agent = create_orchestrator_agent()
    print("Orchestrator Agent initialized successfully.")
except Exception as e:
    print(f"Failed to initialize Orchestrator Agent: {e}")
    agent = None

class UserRequest(BaseModel):
    text: str
    image_url: Optional[str] = None

class AgentResponse(BaseModel):
    text_response: str
    audio_data: Optional[str] = None

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Janus Backend"}

@app.post("/process", response_model=AgentResponse)
async def process_request(request: UserRequest):
    """
    Main entry point for the frontend.
    Receives user instruction and optional current image context.
    """
    print(f"Incoming request: {request.text}, Image: {request.image_url}")
    
    if agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized correctly.")

    try:
        # Construct the input for the agent
        # We include the image URL in the prompt so the agent can pass it to the 'analyze_latest_image' tool if needed.
        input_prompt = request.text
        if request.image_url:
            input_prompt += f"\n[Context Info] Current Camera Image URL: {request.image_url}"

        # 1. Orchestrate logic using ADK Agent
        # agent.query() manages the Thought -> Action -> Observation loop
        response = agent.query(input=input_prompt)
        
        # The LangchainAgent returns a dict with keys like 'input', 'output', 'intermediate_steps'
        final_text = response.get("output", "I'm sorry, I couldn't generate a response.")
        
        # 2. Generate Audio
        audio_b64 = synthesize_speech(final_text)
        
        return AgentResponse(
            text_response=final_text,
            audio_data=audio_b64
        )
        
    except Exception as e:
        print(f"Error processing request: {e}")
        # In case of error, we might want to return a cleaner message or re-raise
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Cloud Run injects PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
